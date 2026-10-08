"""What the zero-shot model compares a photo against.

Material codes match the backend catalogue. Several phrasings per class are averaged into one
text embedding (prompt ensembling), so no class wins just by having more prompts.

OTHER absorbs photos that are not waste at all (people, rooms, blurred shots). Without it the
softmax has to spread all its mass over the materials, and a selfie would come back as some
material with false confidence.

Grades are judged the same way, once the material is known: the photo is compared with a clean,
a lightly contaminated and a mixed description of that material (GRADE_PROMPTS). That is a
rough hint for the seller, not an assessment, which is why the backend prefills a grade only
above its confidence threshold and the seller always chooses.
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
    "pet_bottles": [
        "a pile of used plastic drinking bottles",
        "crushed PET bottles for recycling",
        "a sack of empty plastic water bottles",
    ],
    "hdpe": [
        "used HDPE plastic cans and drums",
        "a pile of plastic crates and containers",
        "old plastic jerry cans for recycling",
    ],
    "occ_cardboard": [
        "a pile of old cardboard boxes",
        "flattened corrugated cartons in bales",
        "waste cardboard for recycling",
    ],
    "glass_cullet": [
        "a pile of used glass bottles",
        "broken glass cullet for recycling",
        "empty glass jars and bottles in a crate",
    ],
    "textile_waste": [
        "a pile of old clothes and fabric scraps",
        "textile cuttings from a garment factory",
        "bales of waste cloth for recycling",
    ],
    "organic_waste": [
        "a pile of food and vegetable waste",
        "garden and market waste for compost",
        "organic kitchen waste in a bin",
    ],
    "e_waste_boards": [
        "electronic waste and circuit boards",
        "a pile of old computer motherboards",
        "scrap printed circuit boards",
    ],
    "lead_acid_batteries": [
        "used car batteries stacked for recycling",
        "old lead acid inverter batteries",
        "a pile of scrap vehicle batteries",
    ],
    OTHER: [
        "a photo of a person",
        "a photo of a room",
        "a blurry photo",
        "a photo of a street",
    ],
}

METALS = ["copper", "brass", "aluminium", "steel_hms", "cast_iron"]

# How each material is named inside the grade descriptions.
NAMES: dict[str, str] = {
    "copper": "copper scrap",
    "brass": "brass scrap",
    "aluminium": "aluminium scrap",
    "steel_hms": "steel scrap",
    "cast_iron": "cast iron scrap",
    "pet_bottles": "plastic bottles",
    "hdpe": "plastic containers",
    "occ_cardboard": "cardboard",
    "glass_cullet": "glass bottles",
    "textile_waste": "textile waste",
    "organic_waste": "organic waste",
    "e_waste_boards": "circuit boards",
    "lead_acid_batteries": "used batteries",
}

# The backend's grades: A clean and sorted, B minor contamination, C mixed or heavily contaminated.
GRADE_PROMPTS: dict[str, list[str]] = {
    "A": ["clean, sorted {} with nothing else mixed in", "a neat pile of clean {}"],
    "B": ["{} with some dirt, paint, oil or small attachments", "slightly dirty {}"],
    "C": ["mixed, dirty, heavily contaminated {}", "{} mixed with other rubbish"],
}

# Every material code in the backend catalogue (backend/src/scraplink/seed.py). A trained probe
# may learn any of them; training folders must be named with one of these, or OTHER.
MATERIAL_CODES = [code for code in PROMPTS if code != OTHER]
