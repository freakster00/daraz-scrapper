# Daraz Seller Scraper API

This repository contains a small Flask web service that exposes an API
for retrieving seller details from **Daraz Nepal**. Given a search
keyword, the service queries the public Daraz site, parses the search
results and then visits individual product pages to extract the seller
name and location. The results are returned in the same rank order as
shown on the site.

## Endpoints

### `GET /api/search`

Search for products on Daraz and return seller details for the top
results.

**Query Parameters:**

| Name   | Type | Required | Description                                         |
|-------|------|----------|-----------------------------------------------------|
| query | str  | ✔        | Search keywords (e.g. `tooth paste`).               |
| limit | int  | ✖        | Max number of results (default 10, max 50).         |

**Example request:**

```
GET https://your-app.onrender.com/api/search?query=tooth%20paste&limit=5
```

**Response:** JSON array of objects. Each object contains:

- `product_name`: Name of the product as displayed on Daraz.
- `price`: The listed price string (currency symbol included).
- `seller_name`: Name of the seller/store, if available.
- `seller_location`: Location of the seller, if available.
- `product_url`: The absolute URL of the product on Daraz.

## Running locally

Create a virtual environment, install dependencies and run the app:

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

The service will start on http://localhost:5000/. You can then
access `http://localhost:5000/api/search?query=toothpaste` in a
browser or via `curl`.

## Deployment on Render

This repository is ready to be deployed on [Render](https://render.com):

1. Push the code to a Git provider (e.g. GitHub) or upload it to
   Render directly.
2. Create a **Web Service** in Render and connect it to your
   repository.
3. Ensure the build command installs dependencies. A common build
   command is:
   
   ```sh
   pip install -r requirements.txt
   ```
4. Set the start command to rely on the included `Procfile`, e.g.:
   
   ```
   gunicorn app:app
   ```

Render will automatically detect the `Procfile` and use Gunicorn to
serve the Flask app.

## Caveats

This code scrapes a third‑party website and therefore depends on
Daraz's markup. If Daraz changes its HTML structure, the CSS
selectors in `scraper.py` may need to be updated. Always use
scraping responsibly: respect robots.txt, rate limit your requests and
consider caching results.