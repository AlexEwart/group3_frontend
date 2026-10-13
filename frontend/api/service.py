import os
from collections.abc import Callable
from typing import Any

import httpx


class FrontendService:
    def __init__(
        self,
        cart_url: str | None = None,
        catalog_url: str | None = None,
        recommendation_url: str | None = None,
        client_factory: Callable[[], httpx.AsyncClient] = httpx.AsyncClient,
    ):
        self.cart_url = (cart_url or os.getenv("CART_SERVICE_URL", "http://localhost:8001")).rstrip("/")
        self.catalog_url = (catalog_url or os.getenv("CATALOG_SERVICE_URL", "http://localhost:8002")).rstrip("/")
        self.recommendation_url = (
            recommendation_url or os.getenv("RECOMMENDATION_SERVICE_URL", "http://localhost:8000")
        ).rstrip("/")
        self.client_factory = client_factory

    async def get_products(self, search_string: str | None = None) -> Any:
        params = {"search_string": search_string} if search_string else None
        async with self.client_factory() as client:
            response = await client.get(f"{self.catalog_url}/products", params=params)
            response.raise_for_status()
            return response.json()

    async def get_cart(self, user_id: str) -> Any:
        async with self.client_factory() as client:
            response = await client.get(f"{self.cart_url}/cart/{user_id}")
            response.raise_for_status()
            return response.json()

    async def add_to_cart(self, user_id: str, product: dict[str, Any]) -> Any:
        # Forward the cart service's product fields using its `price` key.
        cart_product = {
            "product_id": product.get("product_id"),
            "name": product.get("name"),
            "description": product.get("description"),
            "price": product.get("price"),
            "categories": product.get("categories", []),
        }
        async with self.client_factory() as client:
            response = await client.post(
                f"{self.cart_url}/cart/{user_id}",
                json=cart_product,
            )
            response.raise_for_status()
            return response.json()

    async def clear_cart(self, user_id: str) -> Any:
        async with self.client_factory() as client:
            response = await client.delete(f"{self.cart_url}/cart/{user_id}")
            response.raise_for_status()
            return response.json()

    async def get_recommendations(self, user_id: str) -> Any:
        async with self.client_factory() as client:
            response = await client.get(f"{self.recommendation_url}/recommendations/{user_id}")
            response.raise_for_status()
            return response.json()
