from a2a_server.common.base_agent import BaseAgent
from a2a_server.common.models import MathResponseFormat
from a2a_server.common.prompts import MATH_AGENT_PROMPT
from langgraph.prebuilt import create_react_agent
from .tools import add, subtract, multiply, divide, square, cube, power
from logger import logger


class MathAgent(BaseAgent):
    """Math agent for performing arithmetic operations."""

    def __init__(self):
        super().__init__(model_name="gpt-4o-mini", temperature=0.0)

    def get_tools(self):
        """Return math tools."""
        return [add, subtract, multiply, divide, square, cube, power]

    def get_prompt(self):
        """Return the math agent prompt."""
        return MATH_AGENT_PROMPT

    def get_response_format(self):
        """Return the response format."""
        return MathResponseFormat

    async def _initialize_agent(self):
        """Initialize the math agent."""
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
            messages = {"messages": [("user", input_text)]}
            config = {"configurable": {"thread_id": session_id}}

            await self.agent.ainvoke(input=messages, config=config, debug=True)

            result = self.agent.get_state(config).values.get("structured_response")
            return self._process_response(result)

        except Exception as e:
            logger.info(f"Error running agent: {str(e)}")
            return f"Error running query: {str(e)}"

    def _process_response(self, response):
        """Process the math agent's response."""
        if isinstance(response, MathResponseFormat):
            return response.math_output
        return "Unable to process math request"
