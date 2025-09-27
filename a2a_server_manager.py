import asyncio
import signal
import sys
import threading
from typing import Dict, Any
from concurrent.futures import ThreadPoolExecutor

from a2a_server.agents.math_agent_server import MathAgentServer
from a2a_server.agents.weather_agent_server import WeatherAgentServer
from a2a_server.agents.orchestrator_agent_server import OrchestratorServer
from logger import logger


class A2AServerManager:
    """Manages multiple A2A agent servers."""

    def __init__(self):
        self.servers: Dict[str, Dict[str, Any]] = {}
        self.running = False
        self.executor = ThreadPoolExecutor(max_workers=10)

    def add_server(self, name: str, server_class, host: str, port: int):
        """Add a server to the manager."""
        self.servers[name] = {
            "class": server_class,
            "host": host,
            "port": port,
            "instance": None,
            "thread": None,
        }

    def _run_server(self, name: str, server_config: Dict[str, Any]):
        """Run a single server in a thread."""
        try:
            logger.info(
                f"Starting {name} server on {server_config['host']}:{server_config['port']}"
            )
            server = server_config["class"](
                host=server_config["host"], port=server_config["port"]
            )
            server_config["instance"] = server
            server.run()
        except Exception as e:
            logger.error(f"Error running {name} server: {e}")
            raise

    async def start_all(self):
        """Start all registered servers."""
        if self.running:
            logger.warning("Servers are already running")
            return

        logger.info("Starting A2A Server Manager...")
        self.running = True

        # Start all servers in separate threads
        for name, config in self.servers.items():
            thread = threading.Thread(
                target=self._run_server,
                args=(name, config),
                daemon=True,
                name=f"{name}_server_thread",
            )
            thread.start()
            config["thread"] = thread

        # Wait a bit for servers to start
        await asyncio.sleep(2)

        logger.info("All servers started successfully!")

    def stop_all(self):
        """Stop all servers."""
        logger.info("Stopping all servers...")
        self.running = False

    async def run_forever(self):
        """Run servers forever until interrupted."""
        await self.start_all()

        try:
            while self.running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        finally:
            self.stop_all()


def setup_signal_handlers(server_manager: A2AServerManager):
    """Setup signal handlers for graceful shutdown."""

    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}")
        server_manager.stop_all()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


async def main():
    """Main entry point."""
    server_manager = A2AServerManager()

    # Register all agent servers
    server_manager.add_server("Math Agent", MathAgentServer, "localhost", 10004)
    server_manager.add_server("Weather Agent", WeatherAgentServer, "localhost", 10005)
    server_manager.add_server(
        "Orchestrator Agent", OrchestratorServer, "localhost", 10003
    )

    # Setup signal handlers
    setup_signal_handlers(server_manager)

    # Start the server manager
    try:
        await server_manager.run_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Server manager error: {e}")
        raise
    finally:
        server_manager.stop_all()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server shutdown complete")
        sys.exit(0)
