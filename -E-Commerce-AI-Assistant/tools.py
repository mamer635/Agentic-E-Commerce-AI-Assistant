import logging
import pandas as pd

from langchain_core.tools import tool

from schemas import (
    ProductSearchInput,
    ProductCompareInput
)


# =========================
# Logging
# =========================

logger = logging.getLogger(__name__)


# =========================
# Load Product Data
# =========================

df = pd.read_csv("products.csv")

df.columns = df.columns.str.strip()


# =========================
# Search Products
# =========================

@tool(args_schema=ProductSearchInput)
def search_products(query: str) -> str:
    """
    Search products by name, brand, or category.
    """

    query = query.strip().lower()

    logger.info(
        f"Product search: {query}"
    )

    results = df[
        df["name"]
        .astype(str)
        .str.lower()
        .str.contains(query, na=False)
        |
        df["brand"]
        .astype(str)
        .str.lower()
        .str.contains(query, na=False)
        |
        df["category"]
        .astype(str)
        .str.lower()
        .str.contains(query, na=False)
    ]

    if results.empty:

        logger.warning(
            f"No products found: {query}"
        )

        return f"No products found for '{query}'."

    logger.info(
        f"Products found: {len(results)}"
    )

    return results[
        [
            "name",
            "category",
            "brand",
            "price",
            "stock",
            "rating"
        ]
    ].to_string(index=False)


# =========================
# Compare Products
# =========================

@tool(args_schema=ProductCompareInput)
def compare_products(
    product1: str,
    product2: str
) -> str:
    """
    Compare two products.
    """

    logger.info(
        f"Comparing products: {product1} vs {product2}"
    )

    p1 = df[
        df["name"]
        .astype(str)
        .str.lower()
        == product1.strip().lower()
    ]

    p2 = df[
        df["name"]
        .astype(str)
        .str.lower()
        == product2.strip().lower()
    ]

    if p1.empty:

        logger.warning(
            f"Product not found: {product1}"
        )

        return f"Product '{product1}' was not found."

    if p2.empty:

        logger.warning(
            f"Product not found: {product2}"
        )

        return f"Product '{product2}' was not found."

    row1 = p1.iloc[0]
    row2 = p2.iloc[0]

    logger.info(
        f"Comparison completed: {product1} vs {product2}"
    )

    return f"""
Product 1:
Name: {row1['name']}
Brand: {row1['brand']}
Category: {row1['category']}
Price: ${row1['price']}
Stock: {row1['stock']}
Rating: {row1['rating']}

Product 2:
Name: {row2['name']}
Brand: {row2['brand']}
Category: {row2['category']}
Price: ${row2['price']}
Stock: {row2['stock']}
Rating: {row2['rating']}
"""


# =========================
# Get Brands
# =========================

@tool
def get_brands() -> str:
    """
    Return all available brands.
    """

    logger.info("Getting available brands")

    brands = sorted(
        df["brand"]
        .dropna()
        .astype(str)
        .unique()
    )

    logger.info(
        f"Found {len(brands)} brands"
    )

    return "\n".join(brands)


# =========================
# Get Categories
# =========================

@tool
def get_categories() -> str:
    """
    Return all available product categories.
    """

    logger.info("Getting available categories")

    categories = sorted(
        df["category"]
        .dropna()
        .astype(str)
        .unique()
    )

    logger.info(
        f"Found {len(categories)} categories"
    )

    return "\n".join(categories)


# =========================
# Tools List
# =========================

tools = [
    search_products,
    compare_products,
    get_brands,
    get_categories
]