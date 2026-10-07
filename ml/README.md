# ScrapLink ML service

Suggests which metal a lot photo shows, with a confidence score. The backend calls it during
capture (`ML_SERVICE_URL`). A suggestion is prefilled only above
`ML_CLASSIFICATION_CONFIDENCE_THRESHOLD`, and the seller always confirms. If this service is
down, capture carries on with manual selection.

## What it is, honestly

This is a **zero-shot baseline**: OpenAI's CLIP ViT-B/32 (MIT licence) compares the photo
with text descriptions of each metal (`labels.py`). It has never been trained on scrap. It
gives no grade, because judging contamination zero-shot from a photo isn't credible. The seller
chooses the grade.

A rough check on 18 freely licensed Wikimedia Commons photos (2026-10-01) showed what that means
in practice. Most were historical or industrial scenes, not phone shots of a lot, so this is a
sanity check and not a benchmark:

- 16 of 18 scored below 0.75, so they fell back to manual selection. That's the safe failure.
- 2 of 18 scored above 0.75. One was right (a steel scrap yard, 0.87). One was **wrong**: a skip
  of cardboard boxes was called aluminium at 0.83.

So the confidence score isn't calibrated for this domain. That's the realistic-accuracy
problem the research review predicts (Paper 13), and it's why every suggestion goes past a
human. For the pilot, either:

- raise the backend threshold (for example to `0.9`) so prefill is rare, and treat the model
  as a hint shown next to a manual choice, or
- keep `0.75` and rely on the seller's confirmation. A wrong prefill costs one tap to change.

**What replaces it:** a model fine-tuned on pilot photos. The backend already collects the
labelled data, because every confirmed lot stores the photo, the model's suggestion, and the
seller's confirmed metal (custody event `lot.confirmed`, with `suggestion_accepted`). The HTTP
contract below stays the same, so the swap is invisible to the backend.

## Training a better model

Every settled lot is a labelled example: its photo, and the material the seller confirmed and the
buyer accepted at the weighbridge. Two commands turn them into a trained classifier.

```sh
# 1. From backend/: export settled lots' photos and labels (uses DATABASE_URL and MEDIA_DIR)
python -m scraplink.cli export-training --out ../training-data
#    --include-unsettled adds confirmed lots that haven't settled: more photos, noisier labels

# 2. From ml/: train, evaluate on held-out sellers, save the model and a report
python -m scraplink_ml.train --data ../training-data --out models/probe.json
#    --negatives <folder> adds photos that aren't scrap, so they get low confidence
```

Photos from outside the app (a yard visit, a public dataset) go in with `--from-folders`,
repeatable and combinable with `--data`. Sort them one folder per material code, then one folder
per source:

```
yard-photos/
  copper/thrissur-yard/IMG_001.jpg
  brass/kochi-yard/IMG_101.jpg
  other/my-phone/IMG_500.jpg        # photos that aren't scrap
```

Folder names must be the backend's material codes (`labels.MATERIAL_CODES`) or `other`; anything
else stops the run with the list of valid names. Each source stays on one side of the train/test
split, and byte-identical photos are used once, since public datasets often copy each other.

What it does (`train.py`): CLIP stays frozen and turns each photo into features once. A small
linear classifier learns materials from those features, including non-metals if they're in the
data. Each seller's photos go entirely to training or entirely to testing, so the score reflects
new sellers, not memorised yards. The report (`models/probe.report.txt`) gives per-material
precision and recall, the mistakes it made, the zero-shot baseline on the same photos, and the
threshold to set as `ML_CLASSIFICATION_CONFIDENCE_THRESHOLD`. Materials with fewer than
`--min-per-class` photos (default 5) are left out.

To serve it, start the service with `SCRAPLINK_ML_PROBE=models/probe.json`. The HTTP contract
doesn't change, so the backend needs nothing new. Only switch when the report beats the baseline
on a held-out set big enough to trust (the report warns below 30 photos).

## Contract

`POST /classify` with multipart field `image` (JPEG/PNG/WebP, ≤ 10 MB):

```json
{
  "material_code": "copper",
  "grade": null,
  "confidence": 0.8614,
  "looks_like_scrap_metal": true,
  "scores": {"copper": 0.8614, "brass": 0.07, "...": 0.0},
  "model": "openai/clip-vit-base-patch32"
}
```

`material_code` is always the most likely *metal*, with that metal's own probability as
`confidence`. A photo of something else therefore comes back with low confidence, not a
confident guess. The backend reads only the first three fields.

## Running

```sh
python -m venv .venv                       # then activate it
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -e ".[dev]"

uvicorn scraplink_ml.app:create_app --factory --port 8001
pytest                                     # contract tests, no model download
RUN_MODEL_TESTS=1 pytest                   # also loads the real weights (~600 MB first time)
```

First start downloads the weights to the Hugging Face cache. On a laptop CPU a warm request
takes about 0.07 s. Point the backend at `http://127.0.0.1:8001`, not `localhost`: on Windows
`localhost` tries IPv6 first and adds about 2 s to every call.
