from pydantic import BaseModel, Field


class StoreSearchInput(BaseModel):

    query: str = Field(
        description=(
            "Search query for the e-commerce store. "
            "Can include product names, brands, categories, "
            "prices, stock, ratings, warranty, shipping, "
            "delivery, returns, refunds, payments, or store policies."
        )
    )