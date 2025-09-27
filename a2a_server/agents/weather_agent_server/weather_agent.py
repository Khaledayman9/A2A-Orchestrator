from a2a_server.common.base_agent import BaseAgent
from a2a_server.common.models import WeatherResponseFormat
from a2a_server.common.prompts import WEATHER_AGENT_PROMPT
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
import json
from logger import logger


class WeatherAgent(BaseAgent):
    """Weather agent for getting weather information."""

    def __init__(self):
        super().__init__(model_name="gpt-4o", temperature=0.0)

    def get_tools(self):
        """Return weather tools."""
        return []

    def get_prompt(self):
        """Return the weather agent prompt."""
        return WEATHER_AGENT_PROMPT

    def get_response_format(self):
        """Return the response format."""
        return WeatherResponseFormat

    async def _initialize_agent(self):
        try:

            """Initialize the weather agent with MCP tools."""
            # Load MCP configuration
            with open("a2a_server/mcp/servers.json", "r") as f:
                mcp_config = json.load(f)
            logger.info(f"MCP Config: {mcp_config}")
            # Connect to MCP server and get tools
            client = MultiServerMCPClient(mcp_config)
            logger.info("Connecting to MCP server via STDIO...")
            client_tools = await client.get_tools()
            tools = client_tools + self.get_tools()
            logger.info(f"Client tools: {client_tools}")

            # Create the agent with MCP tools
            self.agent = create_react_agent(
                model=self.llm,
                tools=tools,
                prompt=self.get_prompt(),
                debug=True,
                checkpointer=self.memory,
                response_format=self.get_response_format(),
            )
            logger.info("WeatherAgent initialized with MCP tools")
        except Exception as e:
            logger.info(f"Error getting agent: {str(e)}")
            return f"Error running query: {str(e)}"

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
        """Process the weather agent's response."""
        if isinstance(response, WeatherResponseFormat):
            return response.weather_output
        return "Unable to process weather request"
