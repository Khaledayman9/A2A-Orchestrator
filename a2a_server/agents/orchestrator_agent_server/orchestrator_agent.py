import asyncio
from typing import List, Dict, Any, Set
from langgraph.prebuilt import create_react_agent

from a2a_server.common.base_agent import BaseAgent
from a2a_server.common.prompts import ORCHESTRATOR_AGENT_PROMPT
from a2a_server.common.models import OrchestratorResponseFormat, ExecutionPlan, Task
from a2a_server.common.remote_agent_connection import RemoteAgentConnection
from logger import logger


class OrchestratorAgent(BaseAgent):
    """LangGraph-based orchestrator agent with parallel execution support."""

    def __init__(self, remote_agent_addresses: List[str]):
        self.remote_agent_addresses = remote_agent_addresses
        self.remote_connections: Dict[str, RemoteAgentConnection] = {}
        self.available_agents: Dict[str, Dict[str, Any]] = {}

        super().__init__(model_name="gpt-4.1", temperature=0.0)

    def get_tools(self):
        """Return empty list - orchestrator doesn't use tools directly."""
        return []

    def get_prompt(self) -> str:
        """Format available agents for the prompt."""
        descriptions = []
        for name, info in self.available_agents.items():
            skills_str = ""
            if info.get("skills"):
                skills_list = [
                    f"  - {s['name']}: {s['description']}" for s in info["skills"]
                ]
                skills_str = "\n" + "\n".join(skills_list)

            descriptions.append(f"- {name}: {info['description']}{skills_str}")
        agents_description = "\n".join(descriptions)
        return ORCHESTRATOR_AGENT_PROMPT.format(agents_description=agents_description)

    def get_response_format(self):
        """Return the response format."""
        return OrchestratorResponseFormat

    async def _initialize_agent(self):
        """Initialize the orchestrator agent and remote connections."""
        for address in self.remote_agent_addresses:
            try:
                connection = await RemoteAgentConnection.create_from_url(address)
                card = connection.card

                self.remote_connections[card.name] = connection

                # Store agent capabilities for planning
                self.available_agents[card.name] = {
                    "description": card.description,
                    "skills": (
                        [
                            {
                                "name": skill.name,
                                "description": skill.description,
                                "examples": skill.examples,
                            }
                            for skill in card.skills
                        ]
                        if card.skills
                        else []
                    ),
                }
                logger.info(f"Connected to agent: {card.name} at {address}")
            except Exception as e:
                logger.error(f"Failed to connect to {address}: {e}")

        self.agent = create_react_agent(
            model=self.llm,
            tools=self.get_tools(),
            prompt=self.get_prompt(),
            debug=True,
            checkpointer=self.memory,
            response_format=self.get_response_format(),
        )

    async def invoke_agent(self, input_text: str, session_id: str):
        try:
            # Agent initialization is now handled by _ensure_initialized
            logger.info("Available agents:", self.available_agents)

            messages = {"messages": [("user", input_text)]}
            config = {"configurable": {"thread_id": session_id}}

            await self.agent.ainvoke(input=messages, config=config, debug=True)

            result = self.agent.get_state(config).values.get("structured_response")
            return self._process_response(result)

        except Exception as e:
            logger.info(f"Error running agent: {str(e)}")
            return f"Error running query: {str(e)}"

    def _process_response(self, response) -> Dict[str, Any]:
        """Process the orchestrator's response and normalize status."""
        if response and isinstance(response, OrchestratorResponseFormat):
            response_dict = response.model_dump()

            # Treat 'planning' as 'ready' if a plan exists
            if response_dict.get("status") == "planning" and response_dict.get("plan"):
                response_dict["status"] = "ready"

            return response_dict

        return {"status": "error", "error": "Unable to create execution plan"}

    def _build_execution_graph(self, tasks: List[Task]) -> Dict[int, List[int]]:
        """Build a dependency graph for tasks."""
        graph = {}
        for task in tasks:
            graph[task.order] = task.dependencies.copy()
        return graph

    def _find_ready_tasks(
        self, graph: Dict[int, List[int]], completed: Set[int]
    ) -> List[int]:
        """Find tasks that are ready to execute (all dependencies completed)."""
        ready = []
        for task_id, deps in graph.items():
            if task_id not in completed and all(dep in completed for dep in deps):
                ready.append(task_id)
        return ready

    async def execute_plan(self, plan: ExecutionPlan) -> Dict[str, Any]:
        """Execute the plan with parallel execution support."""
        results = {}
        completed_tasks = set()

        # Build task lookup
        task_lookup = {task.order: task for task in plan.tasks}

        # Build dependency graph
        dependency_graph = self._build_execution_graph(plan.tasks)

        logger.info(f"Executing plan with {len(plan.tasks)} tasks")
        logger.info(f"Dependency graph: {dependency_graph}")

        while len(completed_tasks) < len(plan.tasks):
            # Find tasks ready to execute
            ready_tasks = self._find_ready_tasks(dependency_graph, completed_tasks)

            if not ready_tasks:
                # Check for circular dependencies or other issues
                remaining_tasks = set(task_lookup.keys()) - completed_tasks
                logger.error(
                    f"No ready tasks found, but {len(remaining_tasks)} tasks remaining: {remaining_tasks}"
                )
                return {
                    "status": "error",
                    "error": "Circular dependency or unresolvable dependencies detected",
                    "results": results,
                }

            logger.info(
                f"Executing {len(ready_tasks)} tasks in parallel: {ready_tasks}"
            )

            # Execute ready tasks in parallel
            task_coroutines = []
            for task_id in ready_tasks:
                task = task_lookup[task_id]
                coroutine = self._execute_single_task(task, results)
                task_coroutines.append((task_id, coroutine))

            # Wait for all parallel tasks to complete
            task_results = await asyncio.gather(
                *[coro for _, coro in task_coroutines], return_exceptions=True
            )

            # Process results
            for (task_id, _), result in zip(task_coroutines, task_results):
                task = task_lookup[task_id]

                if isinstance(result, Exception):
                    logger.error(f"Task {task_id} failed with exception: {result}")
                    results[task_id] = {
                        "status": "error",
                        "agent": task.agent_name,
                        "task": task.task_description,
                        "result": str(result),
                    }
                else:
                    logger.info(f"Task {task_id} completed successfully")
                    results[task_id] = {
                        "status": "success",
                        "agent": task.agent_name,
                        "task": task.task_description,
                        "result": result,
                    }

                completed_tasks.add(task_id)

            logger.info(f"Completed tasks so far: {completed_tasks}")

        # Check if all tasks completed successfully
        failed_tasks = [
            task_id
            for task_id, result in results.items()
            if result.get("status") == "error"
        ]

        if failed_tasks:
            logger.warning(f"Some tasks failed: {failed_tasks}")
            return {
                "status": "partial_success",
                "summary": f"{plan.summary} (with {len(failed_tasks)} failed tasks)",
                "results": results,
                "failed_tasks": failed_tasks,
            }

        return {"status": "completed", "summary": plan.summary, "results": results}

    def _normalize_agent_name(self, name: str) -> str:
        """Normalize agent name by removing spaces and converting to lowercase."""
        return name.replace(" ", "").lower()

    def _find_agent_by_name(self, agent_name: str) -> str:
        """Find the actual agent name that matches the requested name."""
        normalized_requested = self._normalize_agent_name(agent_name)
        for actual_name in self.remote_connections.keys():
            if self._normalize_agent_name(actual_name) == normalized_requested:
                return actual_name

        return None

    async def _execute_single_task(
        self, task: Task, previous_results: Dict[int, Any]
    ) -> str:
        """Execute a single task."""
        try:
            if task.agent_name not in self.remote_connections:
                raise Exception(f"Agent {task.agent_name} not available")

            actual_agent_name = self._find_agent_by_name(task.agent_name)

            if not actual_agent_name:
                available_agents = list(self.remote_connections.keys())
                raise Exception(
                    f"Agent '{task.agent_name}' not found. Available agents: {available_agents}"
                )

            connection = self.remote_connections[actual_agent_name]

            processed_input = self._process_task_input(task, previous_results)

            logger.info(
                f"Executing task {task.order} on {actual_agent_name}: {processed_input}"
            )
            result = await self._call_remote_agent(connection, processed_input)
            logger.info(f"Task {task.order} result: {result}")

            return result

        except Exception as e:
            logger.error(f"Error executing task {task.order}: {e}")
            raise

    def _process_task_input(self, task: Task, previous_results: Dict[int, Any]) -> str:
        """Process task input, potentially incorporating results from dependencies."""
        processed_input = task.task_input

        if task.dependencies and previous_results:
            dependency_context = []
            for dep_id in task.dependencies:
                if (
                    dep_id in previous_results
                    and previous_results[dep_id].get("status") == "success"
                ):
                    dep_result = previous_results[dep_id].get("result", "")
                    dependency_context.append(
                        f"Previous result from task {dep_id}: {dep_result}"
                    )

            if dependency_context:
                context_str = "\n".join(dependency_context)
                processed_input = f"{context_str}\n\nNow: {processed_input}"

        return processed_input

    def _extract_text_from_response(self, response) -> str:
        """Extract clean text from a message response object."""
        try:
            # Handle the response object structure
            if hasattr(response, "root") and hasattr(response.root, "result"):
                # This is a SendMessageResponse
                message = response.root.result
            else:
                # This might be the message directly
                message = response

            # Extract text from message parts
            if hasattr(message, "parts") and message.parts:
                for part in message.parts:
                    if hasattr(part, "root") and hasattr(part.root, "text"):
                        return part.root.text.strip()

            # Fallback: try to get text content directly
            if hasattr(message, "text"):
                return message.text.strip()

            # If we can't extract text, return string representation
            return str(message)

        except Exception as e:
            logger.warning(f"Error extracting text from response: {e}")
            return str(response)

    async def _call_remote_agent(
        self, connection: RemoteAgentConnection, task_text: str
    ) -> str:
        """Call a remote agent and get the response."""

        response = await connection.send_message(task_text)

        # Extract clean text from response instead of raw object
        return self._extract_text_from_response(response)

    async def process_query(self, query: str, session_id: str) -> Dict[str, Any]:
        """Process a query through planning and execution."""

        plan_response = await self.invoke_agent(query, session_id)
        logger.info(f"Plan response: {plan_response}")

        if isinstance(plan_response, dict):
            if plan_response.get("status") == "ready" and plan_response.get("plan"):
                execution_result = await self.execute_plan(
                    ExecutionPlan(**plan_response["plan"])
                )
                logger.info(f"Execution result: {execution_result}")
                return execution_result
            else:
                return plan_response

        return {"status": "error", "error": "Unexpected response format"}
