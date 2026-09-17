import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from graph import build_graph

from memory import (
    init_memory,
    create_conversation,
    update_conversation_title,
    save_message,
    get_conversations,
    get_conversation,
    delete_conversation,
)

from long_term_memory import (
    init_long_term_memory,
    get_user_memories,
    delete_memory,
    clear_user_memories,
)


# =========================================================
# Logging
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)


# =========================================================
# Configuration
# =========================================================

DEFAULT_USER_ID = "default_user"

CHECKPOINT_DB = "checkpoints.db"


# =========================================================
# Lifespan
# =========================================================

@asynccontextmanager
async def lifespan(app: FastAPI):

    logger.info("Starting application...")

    # -----------------------------------------------------
    # Initialize databases
    # -----------------------------------------------------

    await init_memory()

    await init_long_term_memory()

    logger.info("Memory databases initialized")

    # -----------------------------------------------------
    # LangGraph Checkpointer
    # -----------------------------------------------------

    async with AsyncSqliteSaver.from_conn_string(
        CHECKPOINT_DB
    ) as checkpointer:

        await checkpointer.setup()

        logger.info(
            "LangGraph checkpointer initialized"
        )

        # -------------------------------------------------
        # Build graph
        # -------------------------------------------------

        app.state.graph = build_graph(
            checkpointer
        )

        logger.info(
            "LangGraph ready"
        )

        yield

    logger.info(
        "LangGraph checkpointer closed"
    )

    logger.info(
        "Application shutdown complete"
    )


# =========================================================
# FastAPI
# =========================================================

app = FastAPI(
    title="ShopAI",
    description="E-commerce AI Assistant",
    version="1.0.0",
    lifespan=lifespan,
)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# Health
# =========================================================

@app.get("/health")
async def health():

    return {
        "status": "ok",
        "service": "ShopAI",
    }


# =========================================================
# Create Conversation
# =========================================================

@app.post("/conversations")
async def create_new_conversation(
    request: Request
):

    try:

        data = await request.json()

        session_id = (
            data.get("session_id")
            or data.get("sessionId")
        )

        if not session_id:

            raise HTTPException(
                status_code=400,
                detail="session_id is required",
            )

        conversation = await create_conversation(
            session_id=session_id
        )

        return {
            "success": True,
            "conversation": conversation,
        }

    except HTTPException:
        raise

    except Exception as e:

        logger.exception(
            "Error creating conversation"
        )

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


# =========================================================
# Get Conversations
# =========================================================

@app.get("/conversations")
async def conversations():

    try:

        result = await get_conversations()

        return {
            "success": True,
            "conversations": result,
        }

    except Exception as e:

        logger.exception(
            "Error loading conversations"
        )

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


# =========================================================
# Get One Conversation
# =========================================================

@app.get("/conversations/{session_id}")
async def get_one_conversation(
    session_id: str
):

    try:

        conversation = await get_conversation(
            session_id
        )

        if conversation is None:

            raise HTTPException(
                status_code=404,
                detail="Conversation not found",
            )

        return conversation

    except HTTPException:
        raise

    except Exception as e:

        logger.exception(
            "Error loading conversation"
        )

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


# =========================================================
# Delete Conversation
# =========================================================

@app.delete("/conversations/{session_id}")
async def remove_conversation(
    session_id: str
):

    try:

        deleted = await delete_conversation(
            session_id
        )

        if not deleted:

            raise HTTPException(
                status_code=404,
                detail="Conversation not found",
            )

        return {
            "success": True,
            "message": "Conversation deleted",
        }

    except HTTPException:
        raise

    except Exception as e:

        logger.exception(
            "Error deleting conversation"
        )

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


# =========================================================
# Chat
# =========================================================

@app.post("/chat")
async def chat(
    request: Request
):

    try:

        data = await request.json()

        # -------------------------------------------------
        # Support both frontend naming styles
        # -------------------------------------------------

        session_id = (
            data.get("session_id")
            or data.get("sessionId")
        )

        user_message = (
            data.get("message")
            or data.get("query")
        )

        if not session_id:

            raise HTTPException(
                status_code=400,
                detail="session_id is required",
            )

        if not user_message:

            raise HTTPException(
                status_code=400,
                detail="message is required",
            )

        user_message = str(
            user_message
        ).strip()

        if not user_message:

            raise HTTPException(
                status_code=400,
                detail="message cannot be empty",
            )

        logger.info(
            f"User question: {user_message}"
        )

        # -------------------------------------------------
        # Check conversation
        # -------------------------------------------------

        conversation = await get_conversation(
            session_id
        )

        if conversation is None:

            await create_conversation(
                session_id=session_id
            )

        # -------------------------------------------------
        # Save user message
        # -------------------------------------------------

        await save_message(
            session_id=session_id,
            role="user",
            content=user_message,
        )

        # -------------------------------------------------
        # Update title
        # -------------------------------------------------

        if conversation is None:

            title = user_message[:50]

            await update_conversation_title(
                session_id=session_id,
                title=title,
            )

        # -------------------------------------------------
        # LangGraph config
        # -------------------------------------------------

        config = {
            "configurable": {
                "thread_id": session_id
            }
        }

        # -------------------------------------------------
        # Get graph
        # -------------------------------------------------

        graph = app.state.graph

        # -------------------------------------------------
        # Invoke graph
        # -------------------------------------------------

        result = await graph.ainvoke(

            {
                "messages": [
                    {
                        "role": "user",
                        "content": user_message,
                    }
                ],

                "session_id": session_id,

                "user_id": DEFAULT_USER_ID,
            },

            config=config,
        )

        # -------------------------------------------------
        # Get AI response
        # -------------------------------------------------

        messages = result.get(
            "messages",
            []
        )

        if not messages:

            raise RuntimeError(
                "No response generated by graph"
            )

        response_message = messages[-1]

        ai_response = getattr(
            response_message,
            "content",
            str(response_message),
        )

        # -------------------------------------------------
        # Save AI message
        # -------------------------------------------------

        await save_message(
            session_id=session_id,
            role="assistant",
            content=ai_response,
        )

        logger.info(
            "AI response generated successfully"
        )

        return {
            "success": True,
            "response": ai_response,
            "session_id": session_id,
        }

    except HTTPException:
        raise

    except Exception as e:

        logger.exception(
            "Error while processing request"
        )

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


# =========================================================
# Long-Term Memories
# =========================================================

@app.get("/memories")
async def memories():

    try:

        result = await get_user_memories(
            DEFAULT_USER_ID
        )

        return {
            "success": True,
            "memories": result,
        }

    except Exception as e:

        logger.exception(
            "Error loading memories"
        )

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


# =========================================================
# Delete Memory
# =========================================================

@app.delete("/memories/{memory_id}")
async def remove_memory(
    memory_id: str
):

    try:

        await delete_memory(
            memory_id
        )

        return {
            "success": True,
            "message": "Memory deleted",
        }

    except Exception as e:

        logger.exception(
            "Error deleting memory"
        )

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


# =========================================================
# Clear All Memories
# =========================================================

@app.delete("/memories")
async def clear_memories():

    try:

        await clear_user_memories(
            DEFAULT_USER_ID
        )

        return {
            "success": True,
            "message": "All memories deleted",
        }

    except Exception as e:

        logger.exception(
            "Error clearing memories"
        )

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


# =========================================================
# Frontend
# =========================================================

app.mount(
    "/",
    StaticFiles(
        directory="frontend",
        html=True,
    ),
    name="frontend",
)