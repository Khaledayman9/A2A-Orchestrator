from logger import logger
from mcp.server.fastmcp import FastMCP


mcp = FastMCP("Weather")


@mcp.tool()
async def get_weather(location: str) -> str:
    """Get weather information for a specific location.

    Args:
        location: The location to get weather for

    Returns:
        Weather information as a string
    """
    try:
        logger.info(f"Getting weather for: {location}")

        # Simple mock weather response - replace with real API call if needed
        weather_responses = {
            "new york": "Partly cloudy, 22°C (72°F), light wind from the west",
            "cairo": "Sunny and hot, 35°C (95°F), clear skies",
            "london": "Overcast with light rain, 15°C (59°F), humid",
            "tokyo": "Clear skies, 25°C (77°F), gentle breeze",
            "paris": "Cloudy, 18°C (64°F), chance of rain later",
            "other": "Rainy, 12°C (53°F), chance of dusty wind later",
        }

        location_lower = location.lower().strip()

        # Check for exact matches first
        if location_lower in weather_responses:
            weather_info = weather_responses[location_lower]
        else:
            # Check for partial matches
            for key, value in weather_responses.items():
                if key in location_lower or location_lower in key:
                    weather_info = value
                    break
            else:
                # Default response for unknown locations
                weather_info = f"Current weather in {location}: Partly cloudy, 20°C (68°F), moderate conditions"

        result = f"Weather for {location}: {weather_info}"
        logger.info(f"Returning weather: {result}")
        return result

    except Exception as e:
        logger.error(f"Error getting weather for {location}: {e}")
        return f"Sorry, I couldn't get weather information for {location}. Please try again."


@mcp.tool()
async def get_forecast(location: str, days: int = 3) -> str:
    """Get weather forecast for a specific location.

    Args:
        location: The location to get forecast for
        days: Number of days to forecast (1-7)

    Returns:
        Weather forecast as a string
    """
    try:
        logger.info(f"Getting {days}-day forecast for: {location}")

        if days < 1 or days > 7:
            return "Forecast available for 1-7 days only"

        # Mock forecast data
        base_conditions = [
            "Sunny",
            "Partly cloudy",
            "Cloudy",
            "Light rain",
            "Heavy rain",
            "Snow",
            "Thunderstorms",
        ]

        forecast_lines = [f"{days}-day weather forecast for {location}:"]

        for day in range(days):
            day_name = [
                "Today",
                "Tomorrow",
                "Day 3",
                "Day 4",
                "Day 5",
                "Day 6",
                "Day 7",
            ][day]
            condition = base_conditions[day % len(base_conditions)]
            temp_high = 20 + (day * 2) % 15
            temp_low = temp_high - 8

            forecast_lines.append(
                f"{day_name}: {condition}, High {temp_high}°C, Low {temp_low}°C"
            )

        result = "\n".join(forecast_lines)
        logger.info(f"Returning forecast: {result}")
        return result

    except Exception as e:
        logger.error(f"Error getting forecast for {location}: {e}")
        return f"Sorry, I couldn't get forecast information for {location}. Please try again."


if __name__ == "__main__":
    logger.info("Starting Weather MCP Server...")
    mcp.run(transport="stdio")
