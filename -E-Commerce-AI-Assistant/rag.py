import logging
from pathlib import Path
import csv

from langchain_core.documents import Document
from langchain_core.tools import tool

from langchain_text_splitters import (
    RecursiveCharacterTextSplitter
)

from langchain_openai import OpenAIEmbeddings

from langchain_chroma import Chroma

from schemas import StoreSearchInput


# =========================================================
# Logging
# =========================================================

logger = logging.getLogger(__name__)


# =========================================================
# Paths
# =========================================================

KNOWLEDGE_DIR = Path(
    "knowledge"
)

PRODUCTS_FILE = Path(
    "products.csv"
)

CHROMA_DIR = "./chroma_db"

COLLECTION_NAME = (
    "ecommerce_knowledge"
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
# Load Knowledge
# =========================================================

documents = []


logger.info(
    "Loading knowledge files..."
)


if KNOWLEDGE_DIR.exists():

    for file_path in sorted(
        KNOWLEDGE_DIR.glob("*.txt")
    ):

        try:

            text = file_path.read_text(
                encoding="utf-8"
            )

            document = Document(

                page_content=text,

                metadata={
                    "source": file_path.name,
                    "type": "knowledge",
                },

            )

            documents.append(
                document
            )

            logger.info(
                f"Loaded knowledge file: "
                f"{file_path.name}"
            )

        except Exception:

            logger.exception(
                f"Failed to load "
                f"{file_path}"
            )


logger.info(
    f"Total knowledge files: "
    f"{len(documents)}"
)


# =========================================================
# Load Products
# =========================================================

logger.info(
    "Loading products.csv..."
)


if PRODUCTS_FILE.exists():

    with open(
        PRODUCTS_FILE,
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        reader = csv.DictReader(
            file
        )

        product_count = 0

        for row in reader:

            product_count += 1

            content = "\n".join(

                [
                    f"Product Name: {row.get('name', '')}",

                    f"Category: {row.get('category', '')}",

                    f"Brand: {row.get('brand', '')}",

                    f"Price: {row.get('price', '')}",

                    f"Stock: {row.get('stock', '')}",

                    f"Rating: {row.get('rating', '')}",

                ]

            )


            documents.append(

                Document(

                    page_content=content,

                    metadata={
                        "source": "products.csv",
                        "type": "product",
                        "product_name": row.get(
                            "name",
                            ""
                        ),
                    },

                )

            )


    logger.info(
        f"Loaded {product_count} products"
    )


# =========================================================
# Text Splitter
# =========================================================

text_splitter = (
    RecursiveCharacterTextSplitter(

        chunk_size=700,

        chunk_overlap=100,
    )
)


# =========================================================
# Split Documents
# =========================================================

chunks = text_splitter.split_documents(
    documents
)


logger.info(
    f"Created {len(chunks)} "
    f"total document chunks"
)


# =========================================================
# Chroma
# =========================================================

logger.info(
    "Loading Chroma..."
)


vectorstore = Chroma(

    collection_name=COLLECTION_NAME,

    persist_directory=CHROMA_DIR,

    embedding_function=embeddings,
)


# =========================================================
# Insert Documents
# =========================================================

try:

    existing_count = (
        vectorstore._collection.count()
    )

except Exception:

    existing_count = 0


logger.info(
    f"Existing Chroma documents: "
    f"{existing_count}"
)


if existing_count == 0 and chunks:

    logger.info(
        "Adding documents to Chroma..."
    )

    vectorstore.add_documents(
        chunks
    )

    logger.info(
        f"Added {len(chunks)} "
        f"documents to Chroma"
    )


# =========================================================
# Retriever
# =========================================================

retriever = (
    vectorstore.as_retriever(

        search_type="mmr",

        search_kwargs={

            "k": 4,

            "fetch_k": 10,
        },
    )
)


# =========================================================
# Search Tool
# =========================================================

@tool(
    args_schema=StoreSearchInput
)
async def search_store(
    query: str
) -> str:

    """
    Search products and store knowledge.

    This is the only tool used by the agent
    for store information.
    """

    logger.info(
        f"Store search query: {query}"
    )


    docs = await retriever.ainvoke(
        query
    )


    logger.info(
        f"Store search returned "
        f"{len(docs)} documents"
    )


    if not docs:

        return (
            "No store information was found."
        )


    results = []


    for i, document in enumerate(
        docs,
        start=1
    ):

        source = document.metadata.get(
            "source",
            "unknown"
        )


        logger.info(
            f"Store source used: {source}"
        )


        results.append(

            f"""
RESULT {i}

SOURCE:
{source}

CONTENT:
{document.page_content}
"""

        )


    return "\n".join(
        results
    )


# =========================================================
# Tools
# =========================================================

tools = [
    search_store
]