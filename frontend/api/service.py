import logging
import os
from collections.abc import Callable
from typing import Any
from urllib.parse import quote

import httpx


logger = logging.getLogger(__name__)


class FrontendService:
    def __init__(
        self,
        cart_url: str | None = None,
        catalog_url: str | None = None,
        recommendation_url: str | None = None,
        checkout_url: str | None = None,
        client_factory: Callable[[], httpx.AsyncClient] = httpx.AsyncClient,
    ):
        self.cart_url = (cart_url or os.getenv("CART_SERVICE_URL", "http://localhost:8001")).rstrip("/")
        self.catalog_url = (catalog_url or os.getenv("CATALOG_SERVICE_URL", "http://localhost:8002")).rstrip("/")
        self.recommendation_url = (
            recommendation_url or os.getenv("RECOMMENDATION_SERVICE_URL", "http://localhost:8000")
        ).rstrip("/")
        self.checkout_url = (
            checkout_url or os.getenv("CHECKOUT_SERVICE_URL", "http://localhost:8005")
        ).rstrip("/")
        self.client_factory = client_factory

    async def get_products(self, search_string: str | None = None, correlation_id: str | None = None) -> Any:
        params = {"search_string": search_string} if search_string else None
        url = f"{self.catalog_url}/products"
        self._log_correlation("GET", url, correlation_id)
        async with self.client_factory() as client:
            response = await client.get(
                url,
                params=params,
                headers=self._correlation_headers(correlation_id),
            )
            response.raise_for_status()
            return response.json()

    async def get_cart(self, user_id: str, correlation_id: str | None = None) -> Any:
        url = f"{self.cart_url}/cart/{user_id}"
        self._log_correlation("GET", url, correlation_id)
        async with self.client_factory() as client:
            response = await client.get(
                url,
                headers=self._correlation_headers(correlation_id),
            )
            response.raise_for_status()
            return response.json()

    async def add_to_cart(
        self, user_id: str, product: dict[str, Any], correlation_id: str | None = None
    ) -> Any:
        # Forward the cart service's product fields using its `price` key.
        cart_product = {
            "product_id": product.get("product_id"),
            "name": product.get("name"),
            "description": product.get("description"),
            "price": product.get("price"),
            "categories": product.get("categories", []),
        }
        url = f"{self.cart_url}/cart/{user_id}"
        self._log_correlation("POST", url, correlation_id)
        async with self.client_factory() as client:
            response = await client.post(
                url,
                json=cart_product,
                headers=self._correlation_headers(correlation_id),
            )
            response.raise_for_status()
            return response.json()

    async def clear_cart(self, user_id: str, correlation_id: str | None = None) -> Any:
        url = f"{self.cart_url}/cart/{user_id}"
        self._log_correlation("DELETE", url, correlation_id)
        async with self.client_factory() as client:
            response = await client.delete(
                url,
                headers=self._correlation_headers(correlation_id),
            )
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

    async def checkout(
        self,
        user_id: str,
        shipping_address: dict[str, Any],
        card_number: str,
        expiration_date: str,
        svn: str,
        correlation_id: str | None = None,
    ) -> Any:
        url = f"{self.checkout_url}/checkout/{quote(user_id, safe='')}"
        self._log_correlation("POST", url, correlation_id)
        async with self.client_factory() as client:
            response = await client.post(
                url,
                json={
                    "shipping_address": shipping_address,
                    "card_number": card_number,
                    "expiration_date": expiration_date,
                    "svn": svn,
                },
                headers=self._correlation_headers(correlation_id),
            )
            response.raise_for_status()
            return response.json()

    async def get_recommendations(self, user_id: str, correlation_id: str | None = None) -> Any:
        url = f"{self.recommendation_url}/recommendations/{user_id}"
        self._log_correlation("GET", url, correlation_id)
        async with self.client_factory() as client:
            response = await client.get(
                url,
                headers=self._correlation_headers(correlation_id),
            )
            response.raise_for_status()
            return response.json()

    @staticmethod
    def _correlation_headers(correlation_id: str | None) -> dict[str, str]:
        return {"correlation_id": correlation_id} if correlation_id else {}

    @staticmethod
    def _log_correlation(method: str, url: str, correlation_id: str | None) -> None:
        logger.info(
            "Sending correlation_id=%s to %s %s",
            correlation_id or "<none>",
            method,
            url,
        )
