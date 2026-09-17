# 🤖 Agentic E-Commerce AI Assistant

An intelligent e-commerce assistant powered by Large Language Models (LLMs),
Agentic AI, RAG, tool calling, and memory.

The system is designed to understand user requests, retrieve relevant
information, use specialized tools, maintain conversational context,
and handle multi-step tasks in an e-commerce environment.

---

## 🚀 Overview

The Agentic E-Commerce AI Assistant combines Large Language Models with
an agent-based architecture to provide intelligent and context-aware
assistance for e-commerce tasks.

Instead of behaving like a traditional chatbot, the system can:

- Understand natural language requests
- Reason about user queries
- Retrieve relevant information from a knowledge base
- Use specialized tools
- Maintain conversation history
- Store long-term information
- Perform multi-step tasks
- Work with e-commerce product data

---

## ✨ Features

### 🧠 Agentic AI

The system uses an agent-based architecture that allows the LLM to
reason about the user's request and decide which actions or tools
should be used.

### 🔎 Retrieval-Augmented Generation (RAG)

The assistant can retrieve relevant information from a knowledge base
before generating an answer.

RAG helps the system provide responses based on project-specific
information instead of relying only on the LLM's general knowledge.

### 🛠️ Tool Calling

The agent can use specialized tools to perform different operations
and retrieve information required to answer user requests.

### 💾 Short-Term Memory

Conversation history is maintained so the assistant can understand
previous messages and provide context-aware responses.

### 🧠 Long-Term Memory

The system includes long-term memory capabilities for storing and
retrieving useful information across conversations.

### 🛍️ E-Commerce Support

The assistant works with product information and can help users
interact with e-commerce data through natural language.

### 🔗 LangGraph Architecture

LangGraph is used to organize the agent workflow and coordinate
different components such as the LLM, tools, retrieval, and memory.

### 🎨 Frontend

A dedicated frontend interface is included to provide users with
an interactive way to communicate with the AI assistant.

---

## 🏗️ System Architecture

The project follows an agentic workflow where the user's request
passes through the AI agent and the required components are selected
dynamically.

![LangGraph Architecture](langgraph.png)

### Main Components

```text
User
  │
  ▼
Frontend
  │
  ▼
AI Agent
  │
  ├── LLM
  │
  ├── RAG
  │    └── Knowledge Base
  │
  ├── Tools
  │
  ├── Short-Term Memory
  │
  └── Long-Term Memory
  │
  ▼
Final Response
