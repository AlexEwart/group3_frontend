import logging
from pathlib import Path
import re
from uuid import UUID, uuid4

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Any

from .service import FrontendService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Group 3 Frontend")
frontend_service = FrontendService()
STATIC_DIR = Path(__file__).resolve().parents[1] / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class UserSession(BaseModel):
    user_id: str


class ShippingAddress(BaseModel):
    name: str
    street: str
    city: str
    state: str
    zip: int
    country: str


class CheckoutRequest(BaseModel):
    shipping_address: ShippingAddress
    card_number: str
    expiration_date: str
    svn: str


@app.middleware("http")
async def assign_session(request: Request, call_next):
    """Assign a request correlation ID and pass the optional user ID cookie."""
    request.state.user_id = request.cookies.get("shopping_session")
    incoming_id = request.headers.get("correlation-id", "")
    try:
        request.state.correlation_id = str(UUID(incoming_id))
    except (ValueError, AttributeError):
        request.state.correlation_id = str(uuid4())
    response = await call_next(request)
    response.headers["correlation-id"] = request.state.correlation_id
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


@app.get("/api/session")
async def read_session(request: Request):
    return {"user_id": request.state.user_id}


@app.post("/api/session")
async def set_session(session: UserSession, request: Request):
    user_id = session.user_id.strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._@-]{0,79}", user_id):
        raise HTTPException(
            status_code=422,
            detail="Use 1–80 letters, numbers, periods, underscores, @ signs, or hyphens; start with a letter or number.",
        )
    response = JSONResponse({"user_id": user_id})
    response.set_cookie(
        "shopping_session",
        user_id,
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
    )
    return response


def require_user_id(request: Request) -> str:
    user_id = request.state.user_id
    if not user_id:
        raise HTTPException(status_code=401, detail="Enter your user ID first")
    return user_id


@app.get("/api/products")
async def list_products(request: Request, search_string: str | None = None):
    return await call_upstream(
        frontend_service.get_products(search_string, request.state.correlation_id)
    )


@app.get("/api/cart")
async def read_cart(request: Request):
    return await call_upstream(
        frontend_service.get_cart(require_user_id(request), request.state.correlation_id)
    )


@app.post("/api/cart")
async def add_cart_item(item: dict[str, Any], request: Request):
    return await call_upstream(
        frontend_service.add_to_cart(require_user_id(request), item, request.state.correlation_id)
    )


@app.delete("/api/cart")
async def empty_cart(request: Request):
    return await call_upstream(
        frontend_service.clear_cart(require_user_id(request), request.state.correlation_id)
    )


@app.post("/api/checkout")
async def checkout(order: CheckoutRequest, request: Request):
    user_id = require_user_id(request)
    card_number = re.sub(r"[ -]", "", order.card_number)
    if not card_number.isdigit() or not 12 <= len(card_number) <= 19:
        raise HTTPException(status_code=422, detail="Enter a valid card number.")
    if not re.fullmatch(r"(0[1-9]|1[0-2])/(\d{2}|\d{4})", order.expiration_date.strip()):
        raise HTTPException(status_code=422, detail="Enter expiration as MM/YY or MM/YYYY.")
    if not re.fullmatch(r"\d{3,4}", order.svn.strip()):
        raise HTTPException(status_code=422, detail="Enter a valid security code.")

    correlation_id = request.state.correlation_id
    try:
        result = await frontend_service.checkout(
            user_id,
            order.shipping_address.model_dump(),
            card_number,
            order.expiration_date.strip(),
            order.svn.strip(),
            correlation_id,
        )
    except httpx.HTTPStatusError as exc:
        logger.warning("Checkout service returned HTTP %s", exc.response.status_code)
        status_code = exc.response.status_code
        if 400 <= status_code < 500:
            detail = "Checkout was rejected. Check your shipping address and payment details."
        else:
            status_code = 502
            detail = "Checkout service returned an error."
        raise HTTPException(
            status_code=status_code,
            detail=detail,
        ) from exc
    except httpx.HTTPError as exc:
        logger.exception("Checkout service is unavailable")
        raise HTTPException(
            status_code=502,
            detail="Checkout service is unavailable.",
        ) from exc
    return result


@app.get("/api/recommendations")
async def list_recommendations(request: Request):
    return await call_upstream(
        frontend_service.get_recommendations(require_user_id(request), request.state.correlation_id)
    )
