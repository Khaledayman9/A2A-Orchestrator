from a2a_server.common.base_agent_server import BaseAgentServer
from a2a_server.common.base_agent_executor import BaseAgentExecutor
from .math_agent import MathAgent


class MathAgentExecutor(BaseAgentExecutor):
    def __init__(self):
        super().__init__()
        self.agent = MathAgent()

    def get_agent(self):
        return self.agent


class MathAgentServer(BaseAgentServer):
    def get_card_name(self) -> str:
        return "math_agent_card"

    def get_executor(self):
        return MathAgentExecutor()


def main():
    server = MathAgentServer(host="localhost", port=10004)
    server.run()


if __name__ == "__main__":
    main()
