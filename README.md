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

Open `http://localhost:8003`. There is no generated or default user ID. Use the **Sign in** button in the top bar to enter the ID used by the Cart and Recommendation services. Opening the cart while signed out automatically opens the sign-in modal. The ID is kept in an HTTP-only browser-session cookie and is forgotten when the browser session ends. Catalog search updates as you type.

## Configure dependencies

Set these environment variables to the base URLs of the services (without endpoint paths):

| Variable | Default | Used for |
| --- | --- | --- |
| `CART_SERVICE_URL` | `http://localhost:8001` | Cart contents, add, and clear for the entered user ID |
| `CATALOG_SERVICE_URL` | `http://localhost:8002` | Product list and search |
| `RECOMMENDATION_SERVICE_URL` | `http://localhost:8000` | Recommendations for the entered user ID |

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
docker run --rm --name group3-frontend -p 8003:8003 `
  -e CART_SERVICE_URL="http://34.121.75.149:8080" `
  -e CATALOG_SERVICE_URL="https://catalog-264439765988.us-central1.run.app" `
  -e RECOMMENDATION_SERVICE_URL="https://recommendation-264439765988.us-central1.run.app" `
  group3-frontend
```
