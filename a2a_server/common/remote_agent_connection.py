from typing import Callable

import httpx
import uuid
from a2a.client import A2AClient, A2ACardResolver
from a2a.types import (
    AgentCard,
    SendMessageRequest,
    SendMessageResponse,
    Task,
    TaskArtifactUpdateEvent,
    TaskStatusUpdateEvent,
    Message,
    Role,
    Part,
    TextPart,
    MessageSendParams,
)


TaskCallbackArg = Task | TaskStatusUpdateEvent | TaskArtifactUpdateEvent
TaskUpdateCallback = Callable[[TaskCallbackArg, AgentCard], Task]


class RemoteAgentConnection:
    """A class to hold the connections to the remote agents."""

    def __init__(self, agent_card: AgentCard, agent_url: str):
        self._httpx_client = httpx.AsyncClient(timeout=600)
        self.agent_client = A2AClient(self._httpx_client, agent_card, url=agent_url)
        self.card = agent_card
        self.agent_url = agent_url
        self.conversation_name = None
        self.conversation = None
        self.pending_tasks = set()

    @classmethod
    async def create_from_url(cls, agent_url: str) -> "RemoteAgentConnection":
        """Create a RemoteAgentConnections instance by resolving the agent card from URL."""
        async with httpx.AsyncClient(timeout=600) as client:
            card_resolver = A2ACardResolver(client, agent_url)
            card = await card_resolver.get_agent_card()
            return cls(agent_card=card, agent_url=agent_url)

    def get_agent(self) -> AgentCard:
        return self.card

    async def send_message(self, text_message: str) -> SendMessageResponse:
        """Send a text message to the agent."""
        message_id = uuid.uuid4().hex
        message = Message(
            role=Role.user,
            message_id=message_id,
            parts=[Part(root=TextPart(text=text_message))],
        )

        request = SendMessageRequest(
            id=message_id, params=MessageSendParams(message=message)
        )

        return await self.agent_client.send_message(request)

    async def close(self):
        """Close the HTTP client."""
        if self._httpx_client:
            await self._httpx_client.aclose()
