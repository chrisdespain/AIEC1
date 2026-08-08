"""An agent graph with a post-response helpfulness check loop.

After the agent responds, a secondary node evaluates helpfulness. If the
response is helpful, the graph ends; otherwise it loops back for another
attempt, bounded by a safe message-count limit so it cannot loop forever.
"""
from __future__ import annotations

from langchain_core.messages import AIMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from app.models import get_chat_model
from app.state import MessagesState
from app.tools import get_tool_belt

# Hard cap on total messages in the thread before we force termination,
# regardless of the judge's verdict. Guards against infinite agent<->judge loops.
MAX_MESSAGES = 12


def call_model(state: MessagesState) -> dict:
    """Invoke the model (bound to tools) with the accumulated messages."""
    model = get_chat_model().bind_tools(get_tool_belt())
    response = model.invoke(state["messages"])
    return {"messages": [response]}


def route_to_action_or_helpfulness(state: MessagesState) -> str:
    """Send tool calls to the action node; otherwise run the helpfulness check."""
    last_message = state["messages"][-1]
    if getattr(last_message, "tool_calls", None):
        return "action"
    return "helpfulness"


_helpfulness_prompt = ChatPromptTemplate.from_template(
    "Given an initial user query and a final assistant response, determine "
    "whether the final response is genuinely helpful and answers the query. "
    "Respond with only Y or N.\n\n"
    "Initial Query:\n{initial_query}\n\n"
    "Final Response:\n{final_response}"
)


def helpfulness_node(state: MessagesState) -> dict:
    """Judge the latest response against the original query and record a verdict."""
    if len(state["messages"]) >= MAX_MESSAGES:
        return {"messages": [AIMessage(content="HELPFULNESS:END")]}

    initial_query = state["messages"][0]
    final_response = state["messages"][-1]

    chain = _helpfulness_prompt | get_chat_model() | StrOutputParser()
    verdict = chain.invoke(
        {
            "initial_query": initial_query.content,
            "final_response": final_response.content,
        }
    )

    decision = "Y" if verdict.strip().upper().startswith("Y") else "N"
    return {"messages": [AIMessage(content=f"HELPFULNESS:{decision}")]}


def helpfulness_decision(state: MessagesState) -> str:
    """Route based on the verdict recorded by helpfulness_node."""
    verdict_message = state["messages"][-1].content
    if verdict_message in ("HELPFULNESS:Y", "HELPFULNESS:END"):
        return END
    return "continue"


def build_graph() -> StateGraph:
    """Build an agent graph with an auxiliary helpfulness-check loop."""
    graph = StateGraph(MessagesState)
    graph.add_node("agent", call_model)
    graph.add_node("action", ToolNode(get_tool_belt()))
    graph.add_node("helpfulness", helpfulness_node)

    graph.add_edge(START, "agent")
    graph.add_conditional_edges(
        "agent",
        route_to_action_or_helpfulness,
        {"action": "action", "helpfulness": "helpfulness"},
    )
    graph.add_conditional_edges(
        "helpfulness",
        helpfulness_decision,
        {"continue": "agent", END: END},
    )
    graph.add_edge("action", "agent")
    return graph


graph = build_graph().compile()
