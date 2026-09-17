import logging
import uuid

import aiosqlite

from langchain_openai import OpenAIEmbeddings

from langchain_chroma import Chroma

from langchain_core.documents import Document


# =========================================================
# Logging
# =========================================================

logger = logging.getLogger(__name__)


# =========================================================
# Database
# =========================================================

DB_PATH = (
    "long_term_memory.db"
)


# =========================================================
# Embeddings
# =========================================================

embeddings = OpenAIEmbeddings(

    model="embedding-pool",

    base_url="http://localhost:4000/v1",

    api_key="anything",

    chunk_size=100,
)


# =========================================================
# Chroma
# =========================================================

memory_vectorstore = Chroma(

    collection_name="long_term_memory",

    persist_directory=(
        "./long_term_memory_chroma"
    ),

    embedding_function=embeddings,
)


# =========================================================
# Initialize
# =========================================================

async def init_long_term_memory():

    async with aiosqlite.connect(
        DB_PATH
    ) as db:

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (

                id TEXT PRIMARY KEY,

                user_id TEXT NOT NULL,

                memory TEXT NOT NULL,

                memory_type TEXT
                    DEFAULT 'general',

                created_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP,

                updated_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP

            )
            """
        )

        await db.commit()


    logger.info(
        "Long-term memory database initialized"
    )


# =========================================================
# Save Memory
# =========================================================

async def save_memory(
    user_id: str,
    memory: str,
    memory_type: str = "general",
):

    memory = memory.strip()


    if not memory:

        return


    memory_id = str(
        uuid.uuid4()
    )


    # -----------------------------------------------------
    # SQLite
    # -----------------------------------------------------

    async with aiosqlite.connect(
        DB_PATH
    ) as db:

        await db.execute(

            """
            INSERT INTO memories
            (
                id,
                user_id,
                memory,
                memory_type
            )

            VALUES (?, ?, ?, ?)
            """,

            (
                memory_id,
                user_id,
                memory,
                memory_type,
            ),

        )

        await db.commit()


    # -----------------------------------------------------
    # Chroma
    # -----------------------------------------------------

    document = Document(

        page_content=memory,

        metadata={
            "memory_id": memory_id,
            "user_id": user_id,
            "memory_type": memory_type,
        },

    )


    memory_vectorstore.add_documents(

        documents=[
            document
        ],

        ids=[
            memory_id
        ],
    )


    logger.info(
        f"Long-term memory saved: {memory}"
    )


# =========================================================
# Search Memory
# =========================================================

async def search_long_term_memory(
    user_id: str,
    query: str,
    k: int = 5,
):

    try:

        results = (
            await memory_vectorstore
            .asimilarity_search(
                query,
                k=k,
            )
        )

    except Exception:

        logger.exception(
            "Long-term memory search failed"
        )

        return []


    # -----------------------------------------------------
    # Filter by user
    # -----------------------------------------------------

    results = [

        document

        for document in results

        if document.metadata.get(
            "user_id"
        ) == user_id

    ]


    return results


# =========================================================
# Get User Memories
# =========================================================

async def get_user_memories(
    user_id: str
):

    async with aiosqlite.connect(
        DB_PATH
    ) as db:

        db.row_factory = (
            aiosqlite.Row
        )


        cursor = await db.execute(

            """
            SELECT
                id,
                memory,
                memory_type,
                created_at,
                updated_at

            FROM memories

            WHERE user_id = ?

            ORDER BY updated_at DESC
            """,

            (
                user_id,
            ),

        )


        rows = await cursor.fetchall()


    return [
        dict(row)
        for row in rows
    ]


# =========================================================
# Delete Memory
# =========================================================

async def delete_memory(
    memory_id: str
):

    async with aiosqlite.connect(
        DB_PATH
    ) as db:

        await db.execute(

            """
            DELETE FROM memories
            WHERE id = ?
            """,

            (
                memory_id,
            ),

        )

        await db.commit()


    try:

        memory_vectorstore.delete(

            ids=[
                memory_id
            ]

        )

    except Exception:

        logger.exception(
            "Failed to delete memory "
            "from Chroma"
        )


# =========================================================
# Clear User Memories
# =========================================================

async def clear_user_memories(
    user_id: str
):

    memories = await get_user_memories(
        user_id
    )


    async with aiosqlite.connect(
        DB_PATH
    ) as db:

        await db.execute(

            """
            DELETE FROM memories
            WHERE user_id = ?
            """,

            (
                user_id,
            ),

        )

        await db.commit()


    ids = [
        memory["id"]
        for memory in memories
    ]


    if ids:

        try:

            memory_vectorstore.delete(
                ids=ids
            )

        except Exception:

            logger.exception(
                "Failed to clear "
                "Chroma memories"
            )


# =========================================================
# Format Memories
# =========================================================

def format_memories(
    memories
):

    if not memories:

        return (
            "No long-term memories "
            "were found for this user."
        )


    return "\n\n".join(

        [
            f"- {memory.page_content}"

            for memory in memories
        ]

    )