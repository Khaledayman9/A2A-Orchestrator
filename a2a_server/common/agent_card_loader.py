import json
from typing import Dict, Any
from pathlib import Path
from a2a.types import AgentCard, AgentSkill, AgentCapabilities


class AgentCardLoader:
    """Utility class to load agent cards from JSON files."""

    @staticmethod
    def load_card(card_name: str) -> AgentCard:
        """Load an agent card from the agent_cards directory."""
        base_path = Path(__file__).parent.parent / "agent_cards"
        card_path = base_path / f"{card_name}.json"

        if not card_path.exists():
            raise FileNotFoundError(f"Agent card not found: {card_path}")

        with open(card_path, "r") as f:
            data = json.load(f)

        return AgentCardLoader._parse_card(data)

    @staticmethod
    def _parse_card(data: Dict[str, Any]) -> AgentCard:
        """Parse JSON data into an AgentCard object."""
        skills = []
        if "skills" in data:
            skills = [
                AgentSkill(
                    id=skill["id"],
                    name=skill["name"],
                    description=skill["description"],
                    tags=skill.get("tags", []),
                    examples=skill.get("examples", []),
                )
                for skill in data["skills"]
            ]

        capabilities = AgentCapabilities(
            streaming=data.get("capabilities", {}).get("streaming", False),
            multimodal=data.get("capabilities", {}).get("multimodal", False),
            context_retention=data.get("capabilities", {}).get(
                "contextRetention", True
            ),
        )

        return AgentCard(
            name=data["name"],
            description=data["description"],
            url=data["url"],
            version=data.get("version", "1.0.0"),
            default_input_modes=data.get("defaultInputModes", ["text"]),
            default_output_modes=data.get("defaultOutputModes", ["text"]),
            capabilities=capabilities,
            skills=skills,
            supports_authenticated_extended_card=data.get(
                "supportsAuthenticatedExtendedCard", True
            ),
        )

    @staticmethod
    def list_available_cards() -> list[str]:
        """List all available agent cards."""
        base_path = Path(__file__).parent.parent / "agent_cards"
        cards = []
        for file in base_path.glob("*.json"):
            cards.append(file.stem)
        return cards
