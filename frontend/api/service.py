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
        payment_url: str | None = None,
        client_factory: Callable[[], httpx.AsyncClient] = httpx.AsyncClient,
    ):
        self.cart_url = (cart_url or os.getenv("CART_SERVICE_URL", "http://localhost:8001")).rstrip("/")
        self.catalog_url = (catalog_url or os.getenv("CATALOG_SERVICE_URL", "http://localhost:8002")).rstrip("/")
        self.recommendation_url = (
            recommendation_url or os.getenv("RECOMMENDATION_SERVICE_URL", "http://localhost:8000")
        ).rstrip("/")
        self.payment_url = (payment_url or os.getenv("PAYMENT_SERVICE_URL", "http://localhost:8004")).rstrip("/")
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

    @staticmethod
    def _product_id(value: Any) -> str:
        product_id = value.get("product_id", value.get("id")) if isinstance(value, dict) else value
        if product_id is None:
            return ""
        return str(product_id).removeprefix("product-")

    @classmethod
    def cart_total(cls, cart: Any, products: Any) -> float:
        items = cart if isinstance(cart, list) else []
        if isinstance(cart, dict):
            items = cart.get("items", cart.get("cart", []))
        if isinstance(products, dict):
            products = products.get("value", products.get("products", []))
        if not isinstance(items, list) or not items:
            raise ValueError("Your cart is empty.")
        if not isinstance(products, list):
            raise ValueError("The catalog returned an invalid product list.")

        products_by_id = {
            cls._product_id(product): product
            for product in products
            if isinstance(product, dict) and cls._product_id(product)
        }
        total = 0.0
        for item in items:
            product = products_by_id.get(cls._product_id(item))
            if product is None:
                raise ValueError("A cart item is missing from the catalog; the cart was not charged.")
            try:
                price = float(product["price"])
                quantity = int(item.get("quantity", 1)) if isinstance(item, dict) else 1
            except (KeyError, TypeError, ValueError):
                raise ValueError("A cart item has invalid price or quantity data.") from None
            if price < 0 or quantity < 1:
                raise ValueError("A cart item has invalid price or quantity data.")
            total += price * quantity
        return round(total, 2)

    async def charge(self, amount: float, card_number: str, expiration_date: str, svn: str) -> Any:
        async with self.client_factory() as client:
            response = await client.post(
                f"{self.payment_url}/charges",
                json={
                    "amount": amount,
                    "card_number": card_number,
                    "expiration_date": expiration_date,
                    "svn": svn,
                },
            )
            response.raise_for_status()
            return response.json()

    async def get_recommendations(self, user_id: str) -> Any:
        async with self.client_factory() as client:
            response = await client.get(f"{self.recommendation_url}/recommendations/{user_id}")
            response.raise_for_status()
            return response.json()
