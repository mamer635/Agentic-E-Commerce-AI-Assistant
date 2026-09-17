import logging

from dotenv import load_dotenv

load_dotenv()


from typing import Annotated

from typing_extensions import TypedDict

from langchain_openai import ChatOpenAI

from langchain_core.messages import (
    BaseMessage,
    SystemMessage,
    HumanMessage,
)

from langgraph.graph import (
    StateGraph,
    START,
    END,
)

from langgraph.graph.message import add_messages


from rag import search_store

from prompts import SYSTEM_PROMPT

from memory import (
    get_last_4_summaries,
)

from long_term_memory import (
    search_long_term_memory,
    format_memories,
)


# =========================================================
# Logging
# =========================================================

logger = logging.getLogger(__name__)


# =========================================================
# State
# =========================================================

class AgentState(TypedDict):

    messages: Annotated[
        list[BaseMessage],
        add_messages,
    ]

    session_id: str

    user_id: str


# =========================================================
# LLM
# =========================================================

llm = ChatOpenAI(

    model="agent-pool",

    base_url="http://localhost:4000/v1",

    api_key="anything",

    temperature=0,
)


# =========================================================
# Agent Node
# =========================================================

async def call_model(
    state: AgentState
):

    logger.info(
        "========== AGENT START =========="
    )

    messages = state["messages"]

    session_id = state["session_id"]

    user_id = state["user_id"]


    if not messages:

        raise ValueError(
            "No messages found in state"
        )


    # -----------------------------------------------------
    # Find current user message
    # -----------------------------------------------------

    user_message = None

    for message in reversed(messages):

        if getattr(
            message,
            "type",
            None
        ) == "human":

            user_message = message.content

            break


    if not user_message:

        raise ValueError(
            "No user message found"
        )


    logger.info(
        f"User question: {user_message}"
    )


    # =====================================================
    # Long-Term Memory
    # =====================================================

    long_term_memories = (
        await search_long_term_memory(

            user_id=user_id,

            query=user_message,

            k=5,
        )
    )


    memory_text = format_memories(
        long_term_memories
    )


    # =====================================================
    # Previous Conversation Summaries
    # =====================================================

    summaries = await get_last_4_summaries(
        session_id
    )


    if summaries:

        summary_text = "\n\n".join(

            [

                f"Conversation {i + 1}:\n{summary}"

                for i, summary
                in enumerate(summaries)

            ]
        )

    else:

        summary_text = (
            "No previous conversation summaries were found."
        )


    # =====================================================
    # Store Search
    # =====================================================

    logger.info(
        "Calling search_store"
    )


    search_result = (
        await search_store.ainvoke(

            {
                "query": user_message
            }

        )
    )


    logger.info(
        "search_store completed"
    )


    # =====================================================
    # Dynamic Context
    # =====================================================

    input_message = f"""

LONG-TERM USER MEMORY:

{memory_text}


PREVIOUS CONVERSATION SUMMARIES:

{summary_text}


STORE SEARCH RESULT:

{search_result}


CURRENT USER QUESTION:

{user_message}

"""


    # =====================================================
    # Model Messages
    # =====================================================

    model_messages = [

        # Static instructions
        SystemMessage(
            content=SYSTEM_PROMPT
        ),

        # Previous conversation
        *messages[:-1],

        # Current context + question
        HumanMessage(
            content=input_message
        ),
    ]


    # =====================================================
    # LLM Call
    # =====================================================

    logger.info(
        "Calling LiteLLM agent-pool"
    )


    response = await llm.ainvoke(
        model_messages
    )


    logger.info(
        "LiteLLM response received"
    )


    logger.info(
        "========== AGENT END =========="
    )


    return {
        "messages": [
            response
        ]
    }


# =========================================================
# Build Graph
# =========================================================

def build_graph(
    checkpointer
):

    builder = StateGraph(
        AgentState
    )


    builder.add_node(
        "agent",
        call_model
    )


    builder.add_edge(
        START,
        "agent"
    )


    builder.add_edge(
        "agent",
        END
    )


    graph = builder.compile(
        checkpointer=checkpointer
    )


    logger.info(
        "LangGraph compiled with checkpointer"
    )


    return graph