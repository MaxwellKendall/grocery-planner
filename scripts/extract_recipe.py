#!/usr/bin/env python3
# /// script
# dependencies = ["requests", "beautifulsoup4"]
# ///
"""Extract a recipe from a URL using JSON-LD structured data and write it to recipes/.

Usage:
    python scripts/extract_recipe.py <url>
    python scripts/extract_recipe.py --batch < urls.txt
    python scripts/fetch_board.py BOARD_ID | python scripts/extract_recipe.py --batch

Skips URLs where a recipe file already exists. Skips URLs with no JSON-LD Recipe data.
Writes to recipes/<slug>.md in the repo root.
"""

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

RECIPES_DIR = Path(__file__).parent.parent / "recipes"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

PROTEIN_KEYWORDS = {
    "chicken": "chicken",
    "turkey": "turkey",
    "beef": "beef",
    "steak": "beef",
    "brisket": "beef",
    "pork": "pork",
    "bacon": "pork",
    "sausage": "pork",
    "ham": "pork",
    "salmon": "fish",
    "tuna": "fish",
    "tilapia": "fish",
    "cod": "fish",
    "shrimp": "seafood",
    "scallop": "seafood",
    "crab": "seafood",
    "lobster": "seafood",
    "lamb": "lamb",
    "tofu": "tofu",
    "tempeh": "tofu",
    "lentil": "legume",
    "chickpea": "legume",
    "bean": "legume",
    "egg": "eggs",
}


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def parse_iso_duration(iso):
    """Convert ISO 8601 duration (PT1H30M) to human string (1hr 30min)."""
    if not iso:
        return None
    m = re.match(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?", str(iso))
    if not m:
        return str(iso)
    days, hours, minutes = m.groups()
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}hr")
    if minutes:
        parts.append(f"{minutes}min")
    return " ".join(parts) or str(iso)


def duration_to_minutes(iso):
    if not iso:
        return 0
    m = re.match(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?", str(iso))
    if not m:
        return 0
    days, hours, minutes = m.groups()
    return int(days or 0) * 1440 + int(hours or 0) * 60 + int(minutes or 0)


def infer_effort(total_minutes):
    if total_minutes <= 30:
        return "low"
    elif total_minutes <= 90:
        return "medium"
    else:
        return "high"


def infer_protein(name, ingredients):
    text = (name + " " + " ".join(ingredients)).lower()
    for keyword, protein in PROTEIN_KEYWORDS.items():
        if keyword in text:
            return protein
    return "unknown"


def extract_instructions(raw):
    """Normalize recipeInstructions to a flat list of step strings."""
    if not raw:
        return []
    if isinstance(raw, str):
        return [raw.strip()]
    steps = []
    for item in raw:
        if isinstance(item, str):
            steps.append(item.strip())
        elif isinstance(item, dict):
            if item.get("@type") == "HowToStep":
                steps.append(item.get("text", "").strip())
            elif item.get("@type") == "HowToSection":
                for sub in item.get("itemListElement", []):
                    if isinstance(sub, dict):
                        steps.append(sub.get("text", "").strip())
                    elif isinstance(sub, str):
                        steps.append(sub.strip())
    return [s for s in steps if s]


def extract_tags(recipe):
    tags = []
    for field in ("recipeCategory", "recipeCuisine", "keywords"):
        val = recipe.get(field)
        if not val:
            continue
        if isinstance(val, list):
            tags.extend(val)
        elif isinstance(val, str):
            tags.extend(t.strip() for t in re.split(r"[,;]", val))
    return [slugify(t) for t in tags if t.strip()]


def extract_servings(raw):
    if not raw:
        return None
    if isinstance(raw, (int, float)):
        return int(raw)
    m = re.search(r"\d+", str(raw))
    return int(m.group()) if m else None


def find_recipe_jsonld(html):
    """Find the first Schema.org Recipe object in any JSON-LD block."""
    soup = BeautifulSoup(html, "html.parser")
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        # data can be a single object or a list
        candidates = data if isinstance(data, list) else [data]
        for obj in candidates:
            if obj.get("@type") == "Recipe":
                return obj
            # also check @graph arrays
            for item in obj.get("@graph", []):
                if isinstance(item, dict) and item.get("@type") == "Recipe":
                    return item
    return None


def recipe_to_markdown(recipe, source_url):
    name = recipe.get("name", "Untitled Recipe").strip()
    ingredients = recipe.get("recipeIngredient", [])
    instructions = extract_instructions(recipe.get("recipeInstructions"))
    servings = extract_servings(recipe.get("recipeYield"))
    prep_time = parse_iso_duration(recipe.get("prepTime"))
    cook_time = parse_iso_duration(recipe.get("cookTime"))
    total_minutes = duration_to_minutes(
        recipe.get("totalTime") or recipe.get("cookTime")
    )
    effort = infer_effort(total_minutes)
    protein = infer_protein(name, ingredients)
    tags = extract_tags(recipe)

    lines = []

    # Frontmatter
    lines.append("---")
    lines.append(f"name: {name}")
    lines.append(f"protein: {protein}")
    lines.append(f"servings: {servings or 'unknown'}")
    lines.append(f"effort: {effort}")
    if prep_time:
        lines.append(f"prep_time: {prep_time}")
    if cook_time:
        lines.append(f"cook_time: {cook_time}")
    lines.append("cost_per_serving: ~$X.XX")
    if tags:
        lines.append(f"tags: [{', '.join(tags[:5])}]")
    lines.append(f"source: {source_url}")
    lines.append("---")
    lines.append("")

    # Ingredients
    lines.append("## Ingredients")
    lines.append("")
    for ing in ingredients:
        lines.append(f"- {ing}")
    lines.append("")

    # Instructions
    lines.append("## Instructions")
    lines.append("")
    for i, step in enumerate(instructions, 1):
        lines.append(f"{i}. {step}")

    return "\n".join(lines)


def process_url(url):
    slug = slugify(urlparse(url).path.strip("/").split("/")[-1] or urlparse(url).netloc)
    # check for existing files with this slug as substring to avoid duplicates
    existing = list(RECIPES_DIR.glob(f"*{slug}*.md"))
    if existing:
        print(f"  skip (exists): {existing[0].name}", file=sys.stderr)
        return

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  error fetching {url}: {e}", file=sys.stderr)
        return

    recipe = find_recipe_jsonld(resp.text)
    if not recipe:
        print(f"  no JSON-LD Recipe found: {url}", file=sys.stderr)
        return

    name = recipe.get("name", "").strip()
    if not name:
        print(f"  recipe has no name: {url}", file=sys.stderr)
        return

    filename = slugify(name) + ".md"
    out_path = RECIPES_DIR / filename
    if out_path.exists():
        print(f"  skip (exists): {filename}", file=sys.stderr)
        return

    md = recipe_to_markdown(recipe, url)
    out_path.write_text(md)
    print(f"  wrote: {filename}", file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] != "--batch":
        url = sys.argv[1]
        print(f"Extracting: {url}", file=sys.stderr)
        process_url(url)
    elif len(sys.argv) == 2 and sys.argv[1] == "--batch":
        for line in sys.stdin:
            url = line.strip()
            if url:
                print(f"Extracting: {url}", file=sys.stderr)
                process_url(url)
    else:
        print(__doc__)
        sys.exit(1)
