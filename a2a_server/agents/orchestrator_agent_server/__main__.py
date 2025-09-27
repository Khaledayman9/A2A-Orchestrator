from a2a_server.common.base_agent_server import BaseAgentServer
from a2a_server.common.base_agent_executor import BaseAgentExecutor
from .orchestrator_agent import OrchestratorAgent
from a2a.utils import new_agent_text_message
from logger import logger


class OrchestratorExecutor(BaseAgentExecutor):
    def __init__(self):
        super().__init__()
        # Define remote agent addresses
        remote_agents = [
            "http://localhost:10004",
            "http://localhost:10005",
        ]
        self.agent = OrchestratorAgent(remote_agents)

    def get_agent(self):
        return self.agent

    async def execute(self, context, event_queue):
        """Override to handle orchestrator's special execution flow."""
        try:
            await self._ensure_agent_ready()

            user_input = context.get_user_input()
            session_id = context.context_id or "default"

            # Process through the orchestrator
            result = await self.agent.process_query(user_input, session_id)
            logger.info(f"Orchestrator result: {result}")

            # Format the result for output
            if isinstance(result, dict):
                if result.get("status") == "completed":
                    # Format the execution summary
                    output = (
                        f"Execution Summary: {result.get('summary', 'Completed')}\n\n"
                    )
                    combined_result = []
                    for task_id, task_result in result.get("results", {}).items():
                        output += f"Task {task_id} ({task_result.get('agent')}): {task_result.get('result', 'No result')}\n"
                        combined_result.append(
                            f"{task_result.get('task')} is {task_result.get('result')}"
                        )

                    # Add the combined 'result' field
                    result["result"] = " and ".join(combined_result)
                    result = output
                else:
                    result = str(result)

            await event_queue.enqueue_event(new_agent_text_message(result))

        except Exception as e:
            logger.info(f"Error in orchestrator execution: {e}")
            raise


class OrchestratorServer(BaseAgentServer):
    def get_card_name(self) -> str:
        return "orchestrator_agent_card"

    def get_executor(self):
        return OrchestratorExecutor()


def main():
    server = OrchestratorServer(host="localhost", port=10003)
    server.run()


if __name__ == "__main__":
    main()
