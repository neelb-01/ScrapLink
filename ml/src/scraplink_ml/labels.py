"""What the zero-shot model compares a photo against.

Material codes match the backend catalogue. Several phrasings per class are averaged into one
text embedding (prompt ensembling), so no class wins just by having more prompts.

OTHER absorbs photos that are not scrap metal at all. Without it the softmax has to spread all
its mass over the five metals, and a photo of a cardboard box would come back as some metal
with false confidence.
"""

OTHER = "other"

PROMPTS: dict[str, list[str]] = {
    "copper": [
        "a photo of copper scrap",
        "a pile of scrap copper wire",
        "stripped copper cable in a scrap yard",
        "scrap copper pipes and bus bars",
    ],
    "brass": [
        "a photo of brass scrap",
        "a pile of scrap brass valves and fittings",
        "old yellow brass taps and fittings",
    ],
    "aluminium": [
        "a photo of aluminium scrap",
        "a pile of scrap aluminium sheet and extrusions",
        "crushed aluminium cans",
        "old aluminium utensils and castings",
    ],
    "steel_hms": [
        "a photo of heavy melting steel scrap",
        "a pile of rusty steel scrap",
        "scrap steel beams, plates and pipe offcuts",
    ],
    "cast_iron": [
        "a photo of cast iron scrap",
        "a broken cast iron engine block",
        "scrap cast iron pipes and manhole covers",
    ],
    OTHER: [
        "a photo of plastic waste",
        "a pile of paper and cardboard",
        "electronic waste and circuit boards",
        "a photo of a person",
        "a photo of a room",
        "a blurry photo",
    ],
}

METALS = [code for code in PROMPTS if code != OTHER]

# Every material code in the backend catalogue (backend/src/scraplink/seed.py). A trained probe
# may learn any of them; training folders must be named with one of these, or OTHER.
MATERIAL_CODES = [
    "steel_hms",
    "cast_iron",
    "copper",
    "brass",
    "aluminium",
    "pet_bottles",
    "hdpe",
    "occ_cardboard",
    "e_waste_boards",
    "lead_acid_batteries",
]
