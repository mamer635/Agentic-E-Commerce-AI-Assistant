import logging
from dotenv import load_dotenv
load_dotenv()
from langchain_groq import ChatGroq
from langchain.agents import (
    create_tool_calling_agent,
    AgentExecutor
)
from langchain_core.prompts import ( 
    ChatPromptTemplate, 
    MessagesPlaceholder
)
from rag import tools
from prompts import SYSTEM_PROMPT

# =========================
# Logging
# =========================

logger = logging.getLogger(__name__)

logger.info(
    "Starting E-commerce Agent..."
)

# =========================
# LLM
# =========================

llm = ChatGroq(
    model="openai/gpt-oss-20b",
    temperature=0
)

logger.info(
    "LLM initialized"
)

# =========================
# Prompt
# =========================

prompt = ChatPromptTemplate.from_messages(
    [ ( "system", SYSTEM_PROMPT ),
     
    MessagesPlaceholder( variable_name="chat_history" ),

    ( "human", "{input}" ),

    MessagesPlaceholder( variable_name="agent_scratchpad" )
    ]
)

# =========================
# Agent
# =========================

agent = create_tool_calling_agent(
    llm,
    tools,
    prompt
)


# =========================
# Executor
# =========================

agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=False,
    max_iterations=2
)

logger.info(
    "Agent Executor created successfully"
)