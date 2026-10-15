"""The ScrapLink API as a Vercel Python function.

vercel.json sends every /api/* request here; the web client calls the API under /api, as it
does through the Vite proxy in development.
"""

from fastapi import FastAPI

from scraplink.app import create_app

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/api", create_app())
