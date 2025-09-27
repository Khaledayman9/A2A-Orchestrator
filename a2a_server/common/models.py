from pydantic import BaseModel, Field
from typing import List, Literal, Optional


class MathResponseFormat(BaseModel):
    """Response format for math operations."""

    math_output: str = Field(
        description="Sequence of steps needed to generate the result and the result"
    )


class WeatherResponseFormat(BaseModel):
    """Response format for weather queries."""

    weather_output: str = Field(description="Weather information and analysis")


class Task(BaseModel):
    """Represents a single task in the execution plan."""

    agent_name: str = Field(description="Name of the agent to execute this task")
    task_description: str = Field(description="Description of the task")
    task_input: str = Field(description="Input to send to the agent")
    order: int = Field(description="Order of execution")
    dependencies: List[int] = Field(
        default_factory=list, description="Task IDs this task depends on"
    )


class ExecutionPlan(BaseModel):
    """Execution plan for orchestrator."""

    tasks: List[Task] = Field(description="List of tasks to execute")
    summary: str = Field(description="Summary of the execution plan")


class OrchestratorResponseFormat(BaseModel):
    """Response format for orchestrator agent."""

    status: Literal["planning", "ready", "error", "input_required"] = Field(
        description="Status of the orchestration"
    )
    question: Optional[str] = Field(
        None, description="Question to ask user if more information is needed"
    )
    plan: Optional[ExecutionPlan] = Field(None, description="Execution plan when ready")
    error: Optional[str] = Field(
        None, description="Error message if something went wrong"
    )
