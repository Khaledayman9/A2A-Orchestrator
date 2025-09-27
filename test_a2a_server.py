from a2a_server.common.remote_agent_connection import RemoteAgentConnection
import time
import asyncio
from logger import logger


async def test_single_query(query: str):
    """Test a single query against the orchestrator."""

    connection = None
    try:
        # Connect to orchestrator using RemoteAgentConnections
        orchestrator_url = "http://localhost:10003"
        connection = await RemoteAgentConnection.create_from_url(orchestrator_url)

        logger.info(f"\n🔍 Query: {query}")
        logger.info("=" * 60)

        start_time = time.time()

        # Send to orchestrator
        response = await connection.send_message(query)

        end_time = time.time()
        response_time = end_time - start_time

        # Extract response
        if hasattr(response, "root") and hasattr(response.root, "result"):
            result = response.root.result
            logger.info(f"✓ Success ({response_time:.2f}s)")
            logger.info(f"📝 Result: {result}")
            return True, result
        else:
            logger.info(f"✗ Unexpected response format")
            logger.info(f"📝 Raw response: {response}")
            return False, str(response)

    except Exception as e:
        logger.info(f"✗ Error: {e}")
        return False, str(e)

    finally:
        if connection:
            await connection.close()


async def main():
    """Run simple tests."""

    logger.info("\n🤖 A2A Simple Test")
    logger.info("=" * 60)
    logger.info("Testing orchestrator pipeline...")
    logger.info("Note: Make sure servers are running with: python -m a2a_server")

    # Wait a moment for servers to be ready
    await asyncio.sleep(1)

    # Test queries
    queries = [
        "What is 5 + 7?",
        "What's the weather in Cairo?",
        "Calculate 3 * 4 and tell me the weather in New York",
        "First calculate 3 × 4. Then, using that result as the day number of this month, tell me the weather in Cairo on that day.",
    ]

    results = []

    for i, query in enumerate(queries, 1):
        logger.info(f"\n--- Test {i}/{len(queries)} ---")
        success, result = await test_single_query(query)
        results.append((query, success, result))

        # Small delay between queries
        await asyncio.sleep(1)

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)

    successful = sum(1 for _, success, _ in results if success)

    logger.info(f"Total tests: {len(results)}")
    logger.info(f"Successful: {successful}")
    logger.info(f"Failed: {len(results) - successful}")
    logger.info(f"Success rate: {successful/len(results)*100:.1f}%")

    if successful < len(results):
        logger.info("\nFailed tests:")
        for query, success, result in results:
            if not success:
                logger.info(f"  • {query}: {result}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Test interrupted")
