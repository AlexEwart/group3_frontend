import logging
from pathlib import Path
from uuid import uuid4

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .service import FrontendService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Group 3 Frontend")
frontend_service = FrontendService()
STATIC_DIR = Path(__file__).resolve().parents[1] / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class AddCartItem(BaseModel):
    product_id: str


@app.middleware("http")
async def assign_session(request: Request, call_next):
    """Give each visitor an anonymous, persistent cart session ID."""
    user_id = request.cookies.get("shopping_session") or uuid4().hex
    request.state.user_id = user_id
    response = await call_next(request)
    if not request.cookies.get("shopping_session"):
        response.set_cookie(
            "shopping_session",
            user_id,
            httponly=True,
            samesite="lax",
            secure=request.url.scheme == "https",
            max_age=60 * 60 * 24 * 30,
        )
    return response


async def call_upstream(operation):
    try:
        return await operation
    except httpx.HTTPStatusError as exc:
        logger.warning("A dependent service returned HTTP %s", exc.response.status_code)
        raise HTTPException(status_code=502, detail="A storefront service returned an error") from exc
    except httpx.HTTPError as exc:
        logger.exception("A dependent service is unavailable")
        raise HTTPException(status_code=502, detail="A storefront service is unavailable") from exc


@app.get("/", include_in_schema=False)
async def catalog_page():
    return FileResponse(STATIC_DIR / "catalog.html")


@app.get("/cart", include_in_schema=False)
async def cart_page():
    return FileResponse(STATIC_DIR / "cart.html")


@app.get("/health")
async def health():
    return {"service": "group3_frontend", "status": "ok"}


@app.get("/api/products")
async def list_products(search_string: str | None = None):
    return await call_upstream(frontend_service.get_products(search_string))


@app.get("/api/cart")
async def read_cart(request: Request):
    return await call_upstream(frontend_service.get_cart(request.state.user_id))


@app.post("/api/cart")
async def add_cart_item(item: AddCartItem, request: Request):
    return await call_upstream(frontend_service.add_to_cart(request.state.user_id, item.product_id))


@app.delete("/api/cart")
async def empty_cart(request: Request):
    return await call_upstream(frontend_service.clear_cart(request.state.user_id))


@app.get("/api/recommendations")
async def list_recommendations(request: Request):
    return await call_upstream(frontend_service.get_recommendations(request.state.user_id))
