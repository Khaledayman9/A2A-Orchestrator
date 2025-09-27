from a2a.server.agent_execution import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.utils import new_agent_text_message
from a2a.types import InternalError, UnsupportedOperationError
from a2a.utils.errors import ServerError
from abc import abstractmethod
from logger import logger


class BaseAgentExecutor(AgentExecutor):
    """Base executor class for all agents."""

    def __init__(self):
        self._agent_initialized = False

    @abstractmethod
    def get_agent(self):
        """Return the agent instance."""
        pass

    async def _ensure_agent_ready(self):
        """Ensure the agent is ready for execution."""
        if not self._agent_initialized:
            agent = self.get_agent()
            await agent._ensure_initialized()
            self._agent_initialized = True

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Execute the agent with the given context."""
        try:
            # Ensure agent is ready
            await self._ensure_agent_ready()

            user_input = context.get_user_input()
            session_id = context.context_id or "default"

            logger.info(f"USER INPUT: {user_input}")

            agent = self.get_agent()
            result = await agent.invoke_agent(user_input, session_id)

            # Convert result to string if necessary
            if isinstance(result, dict):
                result = str(result)

            await event_queue.enqueue_event(new_agent_text_message(result))

        except Exception as e:
            logger.error(f"An error occurred while streaming the response: {e}")
            raise ServerError(error=InternalError()) from e

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Cancel operation - not supported by default."""
        raise ServerError(error=UnsupportedOperationError())
