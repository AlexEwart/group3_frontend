# Group 3 Frontend

A small standalone FastAPI storefront with two pages: a searchable product catalog and a cart page with recommendations. The frontend proxies requests through its own `/api` routes, so the browser only talks to this service and does not need CORS configuration for the dependent services.

## Run locally

Start the Cart, Catalog, and Recommendation services first, then run:

```powershell
cd group3_frontend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn frontend.api.router:app --reload --port 8003
```

Open `http://localhost:8003`. Each browser session receives an anonymous cart user ID cookie.

## Configure dependencies

Set these environment variables to the base URLs of the services (without endpoint paths):

| Variable | Default | Used for |
| --- | --- | --- |
| `CART_SERVICE_URL` | `http://localhost:8001` | Cart contents, add, and clear |
| `CATALOG_SERVICE_URL` | `http://localhost:8002` | Product list and search |
| `RECOMMENDATION_SERVICE_URL` | `http://localhost:8000` | Cart recommendations |

For example, with PowerShell:

```powershell
$env:CART_SERVICE_URL = "http://localhost:8001"
$env:CATALOG_SERVICE_URL = "http://localhost:8002"
$env:RECOMMENDATION_SERVICE_URL = "http://localhost:8000"
```

Payment, shipping, checkout, and email URLs are not needed for the requested catalog/cart frontend.

## Docker

Build and run this service independently:

```powershell
docker build -t group3-frontend .
docker run --rm -p 8003:8003 `
  -e CART_SERVICE_URL="http://host.docker.internal:8001" `
  -e CATALOG_SERVICE_URL="http://host.docker.internal:8002" `
  -e RECOMMENDATION_SERVICE_URL="http://host.docker.internal:8000" `
  group3-frontend
```
