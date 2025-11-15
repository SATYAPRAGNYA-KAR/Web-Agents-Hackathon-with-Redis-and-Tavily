"""
This is the main entry point for the backend.
It defines the workflow graph, state, tools, nodes and edges.
"""

import os
from typing import Any, List
from typing_extensions import Literal
from langchain_core.messages import SystemMessage, BaseMessage
from langchain_core.runnables import RunnableConfig
from langchain.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.types import Command
from langgraph.graph import MessagesState
from langgraph.prebuilt import ToolNode
from dotenv import load_dotenv

from tools.news_tools import get_market_news
from tools.geo_utils import distance_km, geo_decay_weight

load_dotenv()

class AgentState(MessagesState):
    """
    Agent state definition
    """
    proverbs: List[str] = []
    tools: List[Any] = []
    user_location: dict | None = None
    market_news: List[dict] | None = None

@tool
def get_weather(location: str):
    """
    Get the weather for a given location.
    """
    return f"The weather for {location} is 70 degrees."

backend_tools = [
    get_weather,
    get_market_news
]

# Extract tool names from backend_tools for comparison
backend_tool_names = [tool.name for tool in backend_tools]


async def chat_node(state: AgentState, config: RunnableConfig) -> Command[Literal["tool_node", "__end__"]]:
    """
    Chat node that handles the conversation.
    Since LLM is disabled, we just pass through messages.
    """
    
    system_message = SystemMessage(
        content=(
            "You are a financial analysis assistant using geospatially-weighted news. "
            "You can help users analyze market news based on their location or specific stock exchanges. "
            "The frontend will call tools directly via the API endpoints."
        )
    )

    # Check if there are any tool calls in the messages
    last_message = state["messages"][-1] if state["messages"] else None
    
    # Since LLM is disabled, just acknowledge and end
    return Command(
        goto=END,
        update={"messages": [system_message]},
    )

def route_to_tool_node(response: BaseMessage):
    """
    Route to tool node if any tool call in the response matches a backend tool name.
    """
    tool_calls = getattr(response, "tool_calls", None)
    if not tool_calls:
        return False

    for tool_call in tool_calls:
        if tool_call.get("name") in backend_tool_names:
            return True
    return False

# Define the workflow graph
workflow = StateGraph(AgentState)
workflow.add_node("chat_node", chat_node)
workflow.add_node("tool_node", ToolNode(tools=backend_tools))
workflow.add_edge("tool_node", "chat_node")
workflow.set_entry_point("chat_node")

graph = workflow.compile()