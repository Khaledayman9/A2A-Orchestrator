from a2a_server.common.base_agent_server import BaseAgentServer
from a2a_server.common.base_agent_executor import BaseAgentExecutor
from .weather_agent import WeatherAgent


class WeatherAgentExecutor(BaseAgentExecutor):
    def __init__(self):
        super().__init__()
        self.agent = WeatherAgent()

    def get_agent(self):
        return self.agent


class WeatherAgentServer(BaseAgentServer):
    def get_card_name(self) -> str:
        return "weather_agent_card"

    def get_executor(self):
        return WeatherAgentExecutor()


def main():
    server = WeatherAgentServer(host="localhost", port=10005)
    server.run()


if __name__ == "__main__":
    main()
