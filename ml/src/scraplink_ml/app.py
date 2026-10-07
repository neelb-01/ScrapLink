"""HTTP service the backend calls — see backend/src/scraplink/classification.py for the contract.

uvicorn scraplink_ml.app:create_app --factory --port 8001
"""

import logging
import os
import time
from typing import Annotated

from fastapi import FastAPI, File, HTTPException, UploadFile

from . import __version__
from .model import ClipEmbedder, ClipScorer, NotAnImage, ProbeScorer, Scorer, load_image, suggest
from .probe import Probe

log = logging.getLogger(__name__)
MAX_BYTES = 10 * 1024 * 1024


def default_scorer() -> Scorer:
    """A trained probe when SCRAPLINK_ML_PROBE names one (see train.py), else zero-shot CLIP."""
    probe_path = os.environ.get("SCRAPLINK_ML_PROBE")
    if probe_path:
        probe = Probe.load(probe_path)
        return ProbeScorer(probe, ClipEmbedder(probe.embedding_model))
    return ClipScorer(os.environ.get("SCRAPLINK_ML_MODEL", "openai/clip-vit-base-patch32"))


def create_app(scorer: Scorer | None = None) -> FastAPI:
    if scorer is None:
        started = time.perf_counter()
        scorer = default_scorer()
        log.warning("loaded %s in %.1fs", scorer.name, time.perf_counter() - started)

    app = FastAPI(title="ScrapLink ML", version=__version__)

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "model": scorer.name}

    @app.post("/classify")
    def classify(image: Annotated[UploadFile, File()]) -> dict:
        data = image.file.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise HTTPException(413, "images must be 10 MB or smaller")
        try:
            picture = load_image(data)
        except NotAnImage as exc:
            raise HTTPException(422, str(exc)) from None
        return {**suggest(scorer.scores(picture)), "model": scorer.name}

    return app
