"""
LangChain Agent Service
"""
from dataclasses import dataclass
import logging

from langchain.agents import create_agent
from langchain.tools import tool, ToolRuntime
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import InMemorySaver

from ..config import settings

logger = logging.getLogger(__name__)


# ============ System Prompt ============
SYSTEM_PROMPT = """You are a helpful AI assistant.

You can help users with various tasks including:
- Answering questions
- Having conversations
- Providing information and explanations
- Helping with general tasks

You also have access to weather tools for demo purposes.

Be concise, helpful, and friendly in your responses.
"""


# ============ Context Schema ============
@dataclass
class Context:
    """Custom runtime context schema."""
    user_id: str


# ============ Weather Tools (demo) ============
@tool
def get_weather_for_location(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}!"


@tool
def get_user_location(runtime: ToolRuntime[Context]) -> str:
    """Retrieve user location based on user ID."""
    user_id = runtime.context.user_id
    return "Florida" if user_id == "1" else "SF"


# ============ Agent Factory ============
def create_simple_agent():
    """Create and return the LangChain agent."""
    
    # Initialize the model
    model = init_chat_model(
        settings.OPENAI_MODEL,
        temperature=settings.OPENAI_TEMPERATURE,
        timeout=settings.OPENAI_TIMEOUT,
        max_tokens=settings.OPENAI_MAX_TOKENS
    )
    
    # Initialize the checkpointer for conversation memory
    checkpointer = InMemorySaver()
    
    logger.info(f"Creating agent with model: {settings.OPENAI_MODEL}")
    
    # Create the agent with weather tools
    agent = create_agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=[
            get_weather_for_location,
            get_user_location,
        ],
        context_schema=Context,
        checkpointer=checkpointer
    )
    
    return agent, checkpointer


# Export Context for use in routes
__all__ = ["create_simple_agent", "Context"]
