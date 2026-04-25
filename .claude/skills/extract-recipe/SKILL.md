---
name: extract-recipe
description: Extract a recipe from a given URL and save it to the recipes/ directory. Fetches the page, parses ingredients and instructions, formats as a household recipe file, and asks before writing.
user-invocable: true
---

# Extract Recipe Skill

Fetch a recipe from a URL and save it to `recipes/` in this repo.

## Usage

```
/extract-recipe https://example.com/some-recipe
```

## Procedure

1. **Fetch the page** — use WebFetch on the provided URL to get the page content
2. **Parse the recipe** — extract:
   - Recipe name
   - Servings / yield
   - Prep time, cook time
   - Ingredients (with quantities and units)
   - Instructions (numbered steps)
   - Infer `protein` from the ingredients (e.g. chicken, salmon, beef, pork, shrimp, tofu, eggs — use the dominant protein or `none` if vegetarian with no clear protein)
   - Infer `effort` from total time and step count: under 30min and ≤6 steps = `low`; 30–60min or 7–12 steps = `medium`; over 60min or 13+ steps = `high`
   - Infer `tags` from the recipe content (e.g. `quick`, `weeknight`, `slow-cooker`, `one-pan`, `meal-prep`)
3. **Derive a filename** — slugify the recipe name (lowercase, hyphens, no special chars), e.g. `sheet-pan-salmon.md`
4. **Check for conflicts** — check if a file with that name already exists in `recipes/` and warn the user if so
5. **Format the recipe** using the household recipe format (see below)
6. **Show the formatted recipe** to the user and ask for confirmation before writing
7. **Write to `recipes/<slug>.md`** after confirmation
8. **Ask the user** if they want to add it to `pinned_recipes` in `config.yaml` (remind them that config.yaml is user-owned and must be edited manually)

## Recipe File Format

```markdown
---
name: [Recipe Name]
protein: [chicken | beef | salmon | pork | shrimp | tofu | eggs | none]
servings: [number]
effort: [low | medium | high]
prep_time: [Xmin | Xhr Xmin]
cook_time: [Xmin | Xhr Xmin]
cost_per_serving: ~$X.XX
tags: [tag1, tag2]
source: [URL]
---

## Ingredients

- X unit ingredient
- X unit ingredient

## Instructions

1. Step one
2. Step two
```

`cost_per_serving` must always be left as `~$X.XX` — never fill in a number. The user or review mode sets this from actual spend data.

## Browser Console Alternative

If WebFetch fails (paywalled, JS-rendered, etc.), the user can run the script in [reference.md](reference.md) in the browser console and paste the output. The script outputs the correct format with `# TODO` placeholders for fields it can't infer — fill those in before confirming to write.

## Important

- Never modify `config.yaml` — tell the user to add pinned_recipes entries themselves
- If the page can't be fetched or the recipe can't be parsed, tell the user specifically what's missing rather than guessing
- If ingredients or quantities are ambiguous, include them as-is and flag them with a `# ?` comment so the user can fix them
- Do not invent or fill in missing data — only write what was on the page
