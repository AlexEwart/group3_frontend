# Group 3 Frontend

A small standalone FastAPI storefront with a searchable product catalog and a cart page with recommendations and checkout. The frontend proxies requests through its own `/api` routes, so the browser only talks to this service and does not need CORS configuration for the dependent services.

## Run locally

Start the Cart, Catalog, Recommendation, and Checkout services first, then run:

```powershell
cd group3_frontend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn frontend.api.router:app --reload --port 8003
```

Open `http://localhost:8003`. There is no generated or default user ID. Use the **Sign in** button in the top bar to enter the ID used by the Cart and Recommendation services. Opening the cart while signed out automatically opens the sign-in modal. The ID is kept in an HTTP-only browser-session cookie and is forgotten when the browser session ends. Catalog search updates as you type.

Each browser API request carries a UUID in the `correlation-id` header. The frontend forwards that ID to dependent services and returns it in the response header for tracing.

## Configure dependencies

Set these environment variables to the base URLs of the services (without endpoint paths):

| Variable | Default | Used for |
| --- | --- | --- |
| `CART_SERVICE_URL` | `http://localhost:8001` | Cart contents, add, and clear for the entered user ID |
| `CATALOG_SERVICE_URL` | `http://localhost:8002` | Product list and search |
| `RECOMMENDATION_SERVICE_URL` | `http://localhost:8000` | Recommendations for the entered user ID |
| `CHECKOUT_SERVICE_URL` | `http://localhost:8005` | Places orders with shipping and payment details |

For example, with PowerShell:

```powershell
$env:CART_SERVICE_URL = "http://localhost:8001"
$env:CATALOG_SERVICE_URL = "http://localhost:8002"
$env:RECOMMENDATION_SERVICE_URL = "http://localhost:8000"
$env:CHECKOUT_SERVICE_URL = "http://localhost:8005"
```

Checkout returns the shipping estimate and order total, which the cart page displays after the order is placed.

## Docker

Build and run this service independently:

```powershell
docker build -t group3-frontend .
docker run --rm --name group3-frontend -p 8003:8003 `
  -e CART_SERVICE_URL="http://34.121.75.149:8080" `
  -e CATALOG_SERVICE_URL="https://catalog-264439765988.us-central1.run.app" `
  -e RECOMMENDATION_SERVICE_URL="https://recommendation-264439765988.us-central1.run.app" `
  -e CHECKOUT_SERVICE_URL="http://34.121.75.149:8081" `
  group3-frontend
```

## Build and deploy with Cloud Build

From this repository's root in Git Bash, set the Artifact Registry and image tag values, then submit the build:

```bash
export REPOSITORY=ewart-microservices-repo
export PROJECTID=ewart-microservices
export REGION=us-central1
export TAG="$(git rev-parse --short HEAD)"

gcloud builds submit \
  --project="$PROJECTID" \
  --region="$REGION" \
  --config=cloudbuild.yaml \
  --substitutions=_ARTIFACT_REGISTRY_REPO="$REPOSITORY",SHORT_SHA="$TAG" \
  .
```

Deploy the image to Cloud Run after the build completes:

```bash
gcloud run deploy group3-frontend \
  --project="$PROJECTID" \
  --image "$REGION-docker.pkg.dev/$PROJECTID/$REPOSITORY/group3-frontend:$TAG" \
  --region "$REGION" \
  --port 8003 \
  --allow-unauthenticated \
  --set-env-vars CART_SERVICE_URL="http://34.121.75.149:8080",CATALOG_SERVICE_URL="https://catalog-264439765988.us-central1.run.app",RECOMMENDATION_SERVICE_URL="https://recommendation-264439765988.us-central1.run.app",CHECKOUT_SERVICE_URL="http://34.121.75.149:8081"
```
