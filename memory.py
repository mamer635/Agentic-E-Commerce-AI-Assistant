import logging
from datetime import datetime

from sqlalchemy import (
    String,
    Text,
    DateTime,
    ForeignKey,
    select,
    delete,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)


# =========================================================
# Logging
# =========================================================

logger = logging.getLogger(__name__)


# =========================================================
# Database Configuration
# =========================================================

DATABASE_URL = "sqlite+aiosqlite:///./chat_memory.db"


# =========================================================
# Base
# =========================================================

class Base(DeclarativeBase):
    pass


# =========================================================
# Conversation Model
# =========================================================

class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    session_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    title: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
    )


# =========================================================
# Message Model
# =========================================================

class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    session_id: Mapped[str] = mapped_column(
        ForeignKey(
            "conversations.session_id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    conversation: Mapped["Conversation"] = relationship(
        back_populates="messages",
    )


# =========================================================
# Engine
# =========================================================

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
)


# =========================================================
# Session Factory
# =========================================================

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# =========================================================
# Initialize Database
# =========================================================

async def init_memory():
    """
    Create database tables if they don't exist.
    """

    async with engine.begin() as conn:
        await conn.run_sync(
            Base.metadata.create_all
        )

    logger.info(
        "Chat memory database initialized"
    )


# =========================================================
# Create Conversation
# =========================================================

async def create_conversation(
    session_id: str,
    title: str = "New Conversation",
):
    """
    Create a new conversation.
    """

    async with AsyncSessionLocal() as session:

        conversation = Conversation(
            session_id=session_id,
            title=title,
        )

        session.add(conversation)

        await session.commit()

        await session.refresh(conversation)

        logger.info(
            f"Conversation created: {session_id}"
        )

        return {
            "id": conversation.id,
            "session_id": conversation.session_id,
            "title": conversation.title,
            "summary": conversation.summary,
            "created_at": conversation.created_at,
            "updated_at": conversation.updated_at,
        }


# =========================================================
# Update Conversation Title
# =========================================================

async def update_conversation_title(
    session_id: str,
    title: str,
):
    """
    Update conversation title.
    """

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            select(Conversation).where(
                Conversation.session_id == session_id
            )
        )

        conversation = result.scalar_one_or_none()

        if conversation is None:
            return False

        conversation.title = title
        conversation.updated_at = datetime.utcnow()

        await session.commit()

        logger.info(
            f"Conversation title updated: {session_id}"
        )

        return True


# =========================================================
# Save Message
# =========================================================

async def save_message(
    session_id: str,
    role: str,
    content: str,
):
    """
    Save user or assistant message.
    """

    async with AsyncSessionLocal() as session:

        # -------------------------------------------------
        # Check conversation
        # -------------------------------------------------

        result = await session.execute(
            select(Conversation).where(
                Conversation.session_id == session_id
            )
        )

        conversation = result.scalar_one_or_none()

        # -------------------------------------------------
        # If conversation doesn't exist, create it
        # -------------------------------------------------

        if conversation is None:

            conversation = Conversation(
                session_id=session_id,
                title="New Conversation",
            )

            session.add(conversation)

            await session.flush()

        # -------------------------------------------------
        # Create message
        # -------------------------------------------------

        message = Message(
            session_id=session_id,
            role=role,
            content=content,
        )

        session.add(message)

        # -------------------------------------------------
        # Update conversation timestamp
        # -------------------------------------------------

        conversation.updated_at = datetime.utcnow()

        await session.commit()

        await session.refresh(message)

        logger.info(
            f"Message saved: {session_id} | {role}"
        )

        return {
            "id": message.id,
            "session_id": message.session_id,
            "role": message.role,
            "content": message.content,
            "created_at": message.created_at,
        }


# =========================================================
# Save Summary
# =========================================================

async def save_summary(
    session_id: str,
    summary: str,
):
    """
    Save/update conversation summary.
    """

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            select(Conversation).where(
                Conversation.session_id == session_id
            )
        )

        conversation = result.scalar_one_or_none()

        if conversation is None:
            return False

        conversation.summary = summary
        conversation.updated_at = datetime.utcnow()

        await session.commit()

        logger.info(
            f"Conversation summary saved: {session_id}"
        )

        return True


# =========================================================
# Get Last 4 Summaries
# =========================================================

async def get_last_4_summaries(
    session_id: str,
):
    """
    Get up to 4 previous conversation summaries.

    The current conversation is excluded.
    """

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            select(Conversation.summary)
            .where(
                Conversation.session_id != session_id,
                Conversation.summary.is_not(None),
                Conversation.summary != "",
            )
            .order_by(
                Conversation.updated_at.desc()
            )
            .limit(4)
        )

        summaries = result.scalars().all()

        return list(summaries)


# =========================================================
# Get Conversations
# =========================================================

async def get_conversations():
    """
    Get all conversations for the sidebar.
    """

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            select(Conversation)
            .order_by(
                Conversation.updated_at.desc()
            )
        )

        conversations = result.scalars().all()

        return [
            {
                "id": conversation.id,
                "session_id": conversation.session_id,
                "title": conversation.title,
                "summary": conversation.summary,
                "created_at": conversation.created_at,
                "updated_at": conversation.updated_at,
            }
            for conversation in conversations
        ]


# =========================================================
# Get One Conversation
# =========================================================

async def get_conversation(
    session_id: str,
):
    """
    Get conversation + messages.
    """

    async with AsyncSessionLocal() as session:

        # -------------------------------------------------
        # Get conversation
        # -------------------------------------------------

        result = await session.execute(
            select(Conversation).where(
                Conversation.session_id == session_id
            )
        )

        conversation = result.scalar_one_or_none()

        if conversation is None:
            return None

        # -------------------------------------------------
        # Get messages
        # -------------------------------------------------

        result = await session.execute(
            select(Message)
            .where(
                Message.session_id == session_id
            )
            .order_by(
                Message.created_at.asc(),
                Message.id.asc(),
            )
        )

        messages = result.scalars().all()

        return {
            "id": conversation.id,
            "session_id": conversation.session_id,
            "title": conversation.title,
            "summary": conversation.summary,
            "created_at": conversation.created_at,
            "updated_at": conversation.updated_at,
            "messages": [
                {
                    "id": message.id,
                    "session_id": message.session_id,
                    "role": message.role,
                    "content": message.content,
                    "created_at": message.created_at,
                }
                for message in messages
            ],
        }


# =========================================================
# Delete Conversation
# =========================================================

async def delete_conversation(
    session_id: str,
):
    """
    Delete conversation and its messages.
    """

    async with AsyncSessionLocal() as session:

        # -------------------------------------------------
        # Find conversation
        # -------------------------------------------------

        result = await session.execute(
            select(Conversation).where(
                Conversation.session_id == session_id
            )
        )

        conversation = result.scalar_one_or_none()

        if conversation is None:
            return False

        # -------------------------------------------------
        # Delete messages
        # -------------------------------------------------

        await session.execute(
            delete(Message).where(
                Message.session_id == session_id
            )
        )

        # -------------------------------------------------
        # Delete conversation
        # -------------------------------------------------

        await session.delete(conversation)

        await session.commit()

        logger.info(
            f"Conversation deleted: {session_id}"
        )

        return True