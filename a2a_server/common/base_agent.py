from abc import ABC, abstractmethod
from typing import Any
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from settings import settings


class BaseAgent(ABC):
    """Base class for all agents in the system."""

    def __init__(
        self,
        model_name: str = "gpt-4o",
        temperature: float = 0.0,
        use_memory: bool = True,
    ):

        if model_name.startswith("gemini"):
            self.llm = ChatGoogleGenerativeAI(
                api_key=settings.GOOGLE_API_KEY,
                model=model_name,
                temperature=temperature,
                max_retries=10,
            )
        elif model_name.startswith("gpt"):
            self.llm = ChatOpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL,
                model=model_name,
                temperature=temperature,
                max_retries=10,
            )

        self.memory = MemorySaver() if use_memory else None
        self.agent = None
        self._initialized = False

    @abstractmethod
    async def _initialize_agent(self):
        """Initialize the agent with tools and configuration. Handle any async setup here."""
        pass

    async def _ensure_initialized(self):
        """Ensure the agent is fully initialized."""
        if not self._initialized:
            await self._initialize_agent()
            self._initialized = True

    @abstractmethod
    def get_tools(self):
        """Return the list of tools for this agent."""
        pass

    @abstractmethod
    def get_prompt(self):
        """Return the prompt for this agent."""
        pass

    @abstractmethod
    def get_response_format(self):
        """Return the response format for this agent."""
        pass

    @abstractmethod
    async def invoke_agent(self, input_text: str, session_id: str) -> Any:
        """Invoke the agent with the given input."""
        pass

    @abstractmethod
    def _process_response(self, response: Any) -> Any:
        """Process the agent's response."""
        pass
