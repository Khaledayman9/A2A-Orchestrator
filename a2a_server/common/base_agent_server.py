import uvicorn
from a2a.server.tasks import InMemoryTaskStore
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.apps import A2AStarletteApplication
from .agent_card_loader import AgentCardLoader
from abc import ABC, abstractmethod
from logger import logger


class BaseAgentServer(ABC):
    """Base class for agent servers."""

    def __init__(self, host: str = "localhost", port: int = 10000):
        self.host = host
        self.port = port

    @abstractmethod
    def get_card_name(self) -> str:
        """Return the name of the agent card to load."""
        pass

    @abstractmethod
    def get_executor(self):
        """Return the executor instance for this agent."""
        pass

    def run(self):
        """Run the agent server."""
        try:
            # Load the agent card from JSON
            card_name = self.get_card_name()
            agent_card = AgentCardLoader.load_card(card_name)

            # Update the URL with the actual host and port
            agent_card.url = f"http://{self.host}:{self.port}/"

            # Create the executor
            executor = self.get_executor()

            # Create the request handler
            request_handler = DefaultRequestHandler(
                agent_executor=executor, task_store=InMemoryTaskStore
            )

            # Create and run the server
            server = A2AStarletteApplication(
                http_handler=request_handler, agent_card=agent_card
            )

            logger.info(f"Starting {card_name} server on {self.host}:{self.port}")
            uvicorn.run(server.build(), host=self.host, port=self.port)

        except Exception as e:
            logger.error(f"An error occurred during server startup: {e}")
            raise
