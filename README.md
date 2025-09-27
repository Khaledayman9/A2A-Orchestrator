# A2A Agent Orchestration System

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
![](https://badge.mcpx.dev?type=server "MCP Server")

A distributed multi-agent system that orchestrates complex tasks across specialized AI agents using A2A (Agent-to-Agent) protocol, MCP (Model Context Protocol) and LangGraph.

## Architecture Overview
![A2A Orchestrator Diagram](https://github.com/user-attachments/assets/ceed8545-1b5a-42d1-bc1e-21fbf3cac288)

```
User Query → Orchestrator Agent → [Math Agent | Weather Agent | ...] → Coordinated Response
```

### System Flow

1. **User Input**: Natural language queries are received by the orchestrator
2. **Planning**: Orchestrator analyzes the query and creates an execution plan
3. **Task Distribution**: Tasks are distributed to appropriate specialized agents
4. **Parallel/Sequential Execution**: Tasks execute based on dependencies
5. **Response Coordination**: Results are combined and returned to the user

## Core Components

### Common Utilities:

#### 1. The BaseAgent:

- Features:

  - **LLM Initialization**: Supports both OpenAI (GPT) and Google (Gemini) models
  - **Memory Management**: Uses LangGraph's `MemorySaver` for conversation persistence
  - **Async Lifecycle**: Handles async initialization with `_ensure_initialized()`
  - **Tool Integration**: Abstract methods for tool and prompt definition
  - **Response Processing**: Standardized response handling pipeline

- Key methods:
  - `_initialize_agent()`: Sets up the LangGraph agent with tools and prompts
  - `invoke_agent()`: Main entry point for processing user input
  - `get_tools()`, `get_prompt()`, `get_response_format()`: Agent-specific implementations

#### 2. BaseAgentExecutor:

- Features:
  - **Context Management**: Processes `RequestContext` with user input and session data
  - **Event Streaming**: Uses `EventQueue` to stream responses back to client
  - **Error Handling**: Converts exceptions to proper A2A error formats
  - **Lifecycle Management**: Ensures agents are properly initialized before execution

#### 3. BaseAgentServer:

- Features:
  - **Agent Card Loading**: Dynamically loads configuration from JSON files
  - **Server Lifecycle**: Manages uvicorn server startup/shutdown
  - **A2A Integration**: Creates `A2AStarletteApplication` with proper handlers
  - **Request Routing**: Uses `DefaultRequestHandler` for A2A protocol compliance

#### 4. Agent Card System:

- Agent cards define:
  - **Capabilities**: What the agent can do (streaming, multimodal, etc.)
  - **Skills**: Specific functions with examples and tags
  - **Endpoints**: URL and communication preferences
  - **Metadata**: Version, description, supported modes

### Agents

#### 1. Orchestrator Agent (Port 10003)

- **Purpose**: Central coordinator that plans and executes complex multi-agent workflows
- **Capabilities**:
  - Query analysis and task decomposition
  - Intelligent agent routing
  - Parallel and sequential task execution
  - Dependency management
- **Model**: GPT-4.1
- **Skills**: Task planning, agent routing

#### 2. Math Agent (Port 10004)

- **Purpose**: Specialized mathematical computation agent
- **Capabilities**: Arithmetic operations and power calculations
- **Tools**: add, subtract, multiply, divide, square, cube, power
- **Model**: GPT-4.1
- **Response Format**: Structured math output with step-by-step solutions

#### 3. Weather Agent (Port 10005)

- **Purpose**: Weather information retrieval using MCP (Model Context Protocol)
- **Capabilities**: Current weather and forecasts
- **Tools**: MCP weather server integration
- **Model**: GPT-4.1
- **Skills**: Weather queries for any location

### Inter-Agent Communication

#### RemoteAgentConnection

The orchestrator communicates with other agents via HTTP using the A2A protocol:

```python
class RemoteAgentConnection:
    """Manages HTTP connections to remote agents"""
```

Communication flow:

1. **Discovery**: `create_from_url()` fetches agent card from `/agent-card` endpoint
2. **Connection**: Establishes persistent HTTP client with 600-second timeout
3. **Message Sending**: `send_message()` sends A2A-formatted requests
4. **Response Processing**: Extracts text from structured A2A response format

#### Message Flow

```
Orchestrator → HTTP POST /send-message → Agent Server
                ↓
            A2A Protocol Message
                ↓
        {
          "id": "unique-id",
          "params": {
            "message": {
              "role": "user",
              "parts": [{"text": "user input"}]
            }
          }
        }
```

### Response Body Structures

#### Task Model

```python
class Task(BaseModel):
    agent_name: str          # Which agent should handle this
    task_description: str    # Human-readable description
    task_input: str         # Actual input to send to agent
    order: int              # Execution sequence number
    dependencies: List[int] # Tasks that must complete first
```

#### ExecutionPlan Model

```python
class ExecutionPlan(BaseModel):
    tasks: List[Task]       # All tasks to execute
    summary: str           # High-level description of plan
```

#### A2A Message Structure

The A2A protocol uses structured messages:

```python
class Message:
    role: Role             # "user" or "assistant"
    message_id: str        # Unique identifier
    parts: List[Part]      # Message content parts

class Part:
    root: Union[TextPart, ImagePart, ...]  # Content payload

class TextPart:
    text: str              # The actual text content
```

#### Response Processing

Agents return structured responses that get processed through multiple layers:

1. **LangGraph Output**: Returns structured format (e.g., `MathResponseFormat`)
2. **Agent Processing**: `_process_response()` extracts relevant content
3. **A2A Wrapping**: Content gets wrapped in A2A message format
4. **HTTP Response**: Final JSON response sent over HTTP

### Execution Pipeline

#### Orchestrator Workflow

1. **Planning Phase**:

   - LLM analyzes query and creates `ExecutionPlan`
   - Tasks assigned to appropriate agents based on capabilities
   - Dependencies calculated for proper ordering

2. **Execution Phase**:

   - Dependency graph built from task relationships
   - Ready tasks (no pending dependencies) identified
   - Parallel execution using `asyncio.gather()`
   - Results collected and dependencies updated

3. **Coordination Phase**:
   - Results from dependent tasks passed to subsequent tasks
   - Final response assembled from all task outputs
   - Summary and status returned to user

#### Parallel vs Sequential Execution

```python
# Parallel (no dependencies)
tasks = [
    Task(agent="Math", input="5+7", dependencies=[]),
    Task(agent="Weather", input="Cairo weather", dependencies=[])
]

# Sequential (task 2 depends on task 1)
tasks = [
    Task(agent="Math", input="5*3", dependencies=[], order=1),
    Task(agent="Weather", input="Weather on day {result}", dependencies=[1], order=2)
]
```

#### Examples

- Case 1: Testing a single agent  
  - **Input:**  
  ```text
  What is 5 + 7?
  ```
  - **Result:**  
  ```text
  Result: context_id=None extensions=None kind='message' message_id='6a628346-4caa-4f2e-be2b-ac75dfc7f01b' metadata=None parts=[Part(root=TextPart(kind='text', metadata=None, text='Execution Summary: A single math calculation task to compute the sum of 5 and 7.\n\nTask 1 (Math Agent): 5 + 7 = 12\n'))] reference_task_ids=None role=<Role.agent: 'agent'> task_id=None
  ```

- Case 2: Testing multiple agents with concurrent tasks
  - **Input:**
  ```text
  Calculate 3 * 4 and tell me the weather in New York
  ```
  - **Result:**
  ```text
  context_id=None extensions=None kind='message' message_id='d59c464a-b0e7-4ef2-9a2b-394a518c7bec' metadata=None parts=[Part(root=TextPart(kind='text', metadata=None, text='Execution Summary: First, calculate 3 * 4 using the Math Agent. Second, get the current weather in New York using the Weather Agent. Both tasks are independent and can be executed in parallel.\n\nTask 1 (Math Agent): 3 * 4 = 12\nTask 2 (Weather Agent): It seems there was an issue retrieving the weather for New York. Could you please try again later?\n'))] reference_task_ids=None role=<Role.agent: 'agent'> task_id=None
  ```

- Case 3: Testing multiple agents with sequential (dependent) tasks
  - **Input:**
  ```text
  First calculate 3 × 4. Then, using that result as the day number of this month, tell me the weather in Cairo on that day.
  ```
  - **Result:**
  ```text
  Result: context_id=None extensions=None kind='message' message_id='406de694-0deb-45be-a360-6f22345e0219' metadata=None parts=[Part(root=TextPart(kind='text', metadata=None, text='Execution Summary: First, calculate 3 × 4 to get 12. Then, get the weather in Cairo on the 12th day of this month.\n\nTask 1 (Math Agent): 3 × 4 = 12\nTask 2 (Weather Agent): The weather forecast for Cairo on the 12th day of this month is currently unavailable. Please try again later or provide additional details for assistance.\n'))] reference_task_ids=None role=<Role.agent: 'agent'> task_id=None
  ```

## Directory Structure

```
A2A/
├── a2a_server/                               # Core package
│   ├── agent_cards/                          # Agent configuration
│   │   ├── math_agent_card.json
│   │   ├── orchestrator_agent_card.json
│   │   └── weather_agent_card.json
│   ├── agents/                               # Agent implementations
│   │   ├── math_agent_server/
│   │   ├── orchestrator_agent_server/
│   │   └── weather_agent_server/
│   ├── common/                               # Shared utilities
│   │   ├── agent_card_loader.py
│   │   ├── base_agent.py
│   │   ├── base_agent_executor.py
│   │   ├── base_agent_server.py
│   │   ├── models.py
│   │   ├── prompts.py
│   │   └── remote_agent_connection.py
│   └── mcp/                                  # Model Context Protocol
│       ├── servers/
│       │   └── weather.py
│       └── servers.json
├── a2a_server_manager.py                     # Main server manager
├── test_a2a_server.py                        # Integration tests
├── logger.py                                 # Debugging code
├── requirements.txt
├── pyproject.toml
├── README.md
└── settings.py
```

## Key Features

### Intelligent Orchestration

- **Dynamic Planning**: Automatically breaks down complex queries into executable tasks
- **Dependency Management**: Handles sequential and parallel task execution
- **Agent Discovery**: Automatically discovers and utilizes available specialized agents

### Parallel Execution

- **Independent Tasks**: Run simultaneously for optimal performance
- **Dependency Resolution**: Sequential execution when tasks depend on previous results
- **Mixed Execution**: Combines parallel and sequential patterns as needed

### Extensible Architecture

- **Plugin System**: Easy to add new specialized agents
- **MCP Integration**: Supports Model Context Protocol for external tool integration
- **Agent Cards**: JSON-based agent capability descriptions

## Example Queries

### Simple Queries

```
"What is 5 + 7?"                    → Math Agent
"What's the weather in Cairo?"      → Weather Agent
```

### Complex Orchestrated Queries

```
"Calculate 3 * 4 and tell me the weather in New York"
→ Parallel execution: Math Agent + Weather Agent

"First calculate 3 × 4. Then tell me the weather in Cairo on day 12"
→ Sequential execution: Math Agent → Weather Agent (with dependency)
```

## Installation & Setup

### Prerequisites

- Python 3.10+
- UV package manager (recommended) or pip

### Environment Setup

1. **Clone and navigate to the project:**

   ```bash
   git clone <repository-url>
   cd A2A-Orchestrator
   ```

2. **Set up environment variables:**
   Create a `.env` file and set environment variables:
   ```python
   # settings.py
   OPENAI_API_KEY = "your-openai-key"
   OPENAI_BASE_URL = "https://api.openai.com/v1"  # Optional
   GOOGLE_API_KEY = "your-google-key"  # For Gemini models
   ```

### Installation Methods

#### Option 1: Using UV (Recommended)

```bash
# Install UV if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

#### Option 2: Using Python/Pip

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Running the System

### Start All Servers

```bash
# Using UV
uv run python a2a_server_manager.py

# Using Python
python a2a_server_manager.py
```

This starts all agent servers simultaneously:

- Orchestrator Agent: localhost:10003
- Math Agent: localhost:10004
- Weather Agent: localhost:10005

### Start Individual Agents (Alternative)

```bash
# Math Agent only
uv run python -m a2a_server.agents.math_agent_server

# Weather Agent only
uv run python -m a2a_server.agents.weather_agent_server

# Orchestrator only
uv run python -m a2a_server.agents.orchestrator_agent_server
```

## Testing

### Run Integration Tests

```bash
# Make sure all servers are running first
python test_a2a_server.py
```

### Manual Testing

```bash
# Test individual agents via HTTP API
curl -X POST http://localhost:10004/send-message \
  -H "Content-Type: application/json" \
  -d '{"message": "Calculate 5 + 7"}'
```

## Configuration

### Agent Cards

Each agent has a JSON configuration card defining:

- Capabilities and skills
- Supported input/output modes
- Tool descriptions and examples
- API endpoints

Example structure:

```json
{
  "name": "Math Agent",
  "description": "Mathematical computation specialist",
  "url": "http://localhost:10004/",
  "skills": [
    {
      "id": "add",
      "name": "Addition",
      "description": "Add two numbers",
      "examples": ["5 + 7", "add 10 and 20"]
    }
  ]
}
```

### MCP Server Configuration

Weather agent uses MCP for external tool integration:

```json
{
  "Weather": {
    "command": "python",
    "args": ["-m", "a2a_server.mcp.servers.weather"],
    "transport": "stdio"
  },
  "Weather (UV)": {
    "command": "uv",
    "args": ["run", "python", "-m", "a2a_server.mcp.servers.weather"],
    "transport": "stdio"
  }
}
```

## Development

### Adding New Agents

1. **Create agent card**: Add JSON configuration to `agent_cards/`
2. **Implement agent**: Extend `BaseAgent` in `agents/`
3. **Create server**: Extend `BaseAgentServer`
4. **Add to manager**: Register in `a2a_server_manager.py`
5. **Update orchestrator**: Agent will be auto-discovered

### Extending Capabilities

1. **Add Tools**: Implement LangChain tools for new capabilities
2. **MCP Integration**: Add external tools via Model Context Protocol
3. **Custom Prompts**: Define agent-specific behavior in `prompts.py`
4. **Response Formats**: Add structured output models in `models.py`

## Dependencies

### Core Stack

- **a2a-sdk**: Agent-to-Agent communication protocol
- **langgraph**: Graph-based agent orchestration
- **langchain**: LLM framework and tool integration
- **fastmcp**: Model Context Protocol implementation
- **pydantic**: Data validation and serialization

### LLM Providers

- **OpenAI**: GPT models (primary)
- **Google**: Gemini models (optional)

### Web Framework

- **FastAPI/Uvicorn**: HTTP server infrastructure
- **httpx**: Async HTTP client for inter-agent communication

## Troubleshooting

### Common Issues

1. **Port conflicts**: Check if ports 10003-10005 are available
2. **Rate Limiting Issues**: Shared API Key Problem
   - **Issue**: All agents use the same OpenAI API key configured in `settings.py`
   - **Impact**: High request volume can trigger 429 "Too Many Requests" errors
3. **Parallel Execution Amplification**: Orchestrator's parallel task execution can send multiple simultaneous requests. Multiplies rate limit pressure during complex queries.
4. **No Streaming Support**: Current implementation lacks real-time streaming
5. **Memory Management**: Uses in-memory storage only

### Debugging

- Enable debug logging in agents
- Check individual agent health endpoints
- Use `test_a2a_server.py` for integration testing

## Performance Considerations

- **Parallel Execution**: Independent tasks run simultaneously
- **Connection Pooling**: HTTP clients reuse connections
- **Memory Management**: Agents use memory savers for conversation state
- **Timeout Handling**: 10-minute timeout for long-running operations

## Security Notes

- **Local Development**: Currently configured for localhost only
- **API Keys**: Store securely and never commit to version control
- **Network Access**: Consider firewall rules for production deployment

## Future Enhancements

- Additional specialized agents (code, research, etc.)
- Enhanced dependency resolution algorithms
- Monitoring and observability features
- Production-ready deployment configurations
- WebSocket support for real-time communication

## License

This project is licensed under the Apache License, Version 2.0 - see the [LICENSE](LICENSE) file for details.

The code in the `common/` directory is from the [Google A2A project](https://github.com/google/A2A) and is also licensed under the Apache License, Version 2.0.

This project also makes use of other open-source libraries (e.g., LangGraph, MCP, FastMCP), which are subject to their respective licenses.

## Acknowledgements

- [MCP](https://github.com/modelcontextprotocol) – For providing the Model Context Protocol that inspired part of the system design.
- [A2A](https://github.com/a2a-project) – For concepts and architecture patterns used in building orchestrators and agents.
- [LangGraph](https://github.com/langchain-ai/langgraph) – For enabling composable agent workflows and structured orchestration.






