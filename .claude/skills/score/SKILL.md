---
name: score
description: Score a specific recipe across all dimensions. Auto-computes effort, bang_for_buck, hospitality, and composite from recipe data. Only asks the user for taste and is_memorized if not already stored.
user-invocable: true
---

# Score Skill

Score a recipe across all dimensions and write results to `recent-recipes.yaml`.
Regenerates `recipe-index.md` after writing.

## Usage

```
/score chicken-carnitas
/score recipes/beef-stew.md
/score crisp-gnocchi-with-sausage-and-peas
```

## Procedure

### 1. Resolve the recipe

Accept a slug (filename stem), partial name, or full path. Search `recipes/` for
a match. If ambiguous, list candidates and ask the user to pick one.

### 2. Read existing ratings

Check `recent-recipes.yaml` for an existing ratings block on this recipe. Note
which fields are already set — do not re-ask for fields that are already present
unless the user explicitly provides new values.

### 3. Auto-compute (always recomputed fresh from recipe data)

**Passive cooking detection**

A passive cooking method means the host is not occupied during cook time. Check:
- `tags` field contains: `slow-cooker`, `instant-pot`, `crockpot`
- Recipe `name` or `## Instructions` text contains: "slow cooker", "instant pot",
  "crock pot", "low and slow", "set and forget"

If passive detected → **hands-on time = `prep_time` only**
If not detected → **hands-on time = `prep_time` + `cook_time`**

Parse time strings: `10min` = 10, `1hr 30min` = 90, `2hr` = 120.

**Effort score (1–5, higher = easier for the cook)**

| Hands-on time | Base score |
|---|---|
| ≤ 15 min | 5 |
| 16–30 min | 4 |
| 31–45 min | 3 |
| 46–60 min | 2 |
| > 60 min | 1 |

Apply +1 if `is_memorized: true` (cap at 5). A memorized recipe has zero friction
from consulting ingredients or instructions.

**Bang-for-buck score (1–5)**

1. Check `cost_per_serving` in recipe frontmatter. If it's a real number (not
   `~$X.XX`), use it directly.
2. Otherwise: look up each ingredient in `prices.json` and estimate total cost ÷
   `servings`. If an ingredient has no price data, use culinary knowledge to
   estimate its cost and flag the total as estimated.
3. Read `cost_per_serving_target` from `config.yaml` (currently $4.00) as benchmark.

| Estimated cost/serving | Score |
|---|---|
| ≤ $2.00 | 5 |
| $2.01–$3.00 | 4 |
| $3.01–$4.00 | 3 |
| $4.01–$5.50 | 2 |
| > $5.50 | 1 |

**Hospitality score (derived)**

```
hospitality = round((effort + bang_for_buck) / 2)
```

A recipe is good for hospitality when the host has time to be present with guests
(not tied to the stove) AND can afford to feed them. Impressiveness is not a
factor — time and affordability are.

**Nutrition score (1–5, auto-computed from ingredients)**

Assess dietary quality based on whole food content vs. heavy fats, sugars, and
refined ingredients:

| Description | Score |
|---|---|
| Mostly vegetables, legumes, lean protein, whole grains, olive oil | 5 |
| Balanced — some veg, lean protein, limited heavy fats | 4 |
| Mixed — decent but notable cheese, butter, or refined carbs | 3 |
| Heavy on cream, cheese, butter, or white starch as the base | 2 |
| Primarily fat/sugar/processed with minimal whole food content | 1 |

Use culinary knowledge to estimate from the ingredient list. Flag as estimated.

**Protein score (1–5, auto-computed from ingredients)**

Assess animal protein content and yield per serving. Plant protein scores lower than
animal protein — this household prioritizes meat/fish/eggs for muscle and satiety goals.

| Description | Score |
|---|---|
| Meat/fish/eggs as primary component, >30g protein/serving | 5 |
| Good animal protein — poultry, shrimp, lean cuts, ~20–30g/serving | 4 |
| Moderate animal protein, OR legume-forward with decent yield (~10–20g) | 3 |
| Legume/plant protein only, or low overall protein (<10g) | 2 |
| Vegetable-only, minimal protein of any kind | 1 |

Use culinary knowledge to estimate from the ingredient list.

**Composite score**

Always computed — taste optional:

```
# with taste
composite = round((taste × 2 + effort + bang_for_buck + hospitality + nutrition + protein) / 7, 1)

# without taste
composite = round((effort + bang_for_buck + hospitality + nutrition + protein) / 5, 1)
```

When taste is present it is weighted 2× as the only human-input signal. Range: 1.0–5.0.

### 4. Ask for user-provided fields only if missing

- `taste` already stored → use it, do not re-ask
- `taste` missing → ask: "Taste rating (1–5)? (skip to leave unrated)"
- `is_memorized` already stored → use it, do not re-ask
- `is_memorized` missing → ask: "Do you know this one by heart? (yes/no)"
- Both missing → ask in one combined prompt
- Both present → skip prompting entirely

`taste` may be omitted or nulled out — say "skip" or "null" to leave it unset.
Composite is always computed: using all 6 dimensions when taste is present, or
the 5 auto-scores alone when taste is absent.

If the user supplies taste or is_memorized as part of the invocation
(e.g., `/score chicken-carnitas taste=5 memorized=yes`), use those values directly
without prompting.

### 5. Show score summary

Display before writing:

```
## Score: [Recipe Name]

Passive cooking: yes (slow-cooker) / no
Memorized: yes (+1 effort bonus applied) / no
Hands-on time: Xmin

taste:         X/5  [stored / just provided]
is_memorized:  yes / no
effort:        X/5  — [e.g. "10min hands-on (passive: IP)"]
bang_for_buck: X/5  — ~$X.XX/serving [estimated / from frontmatter]
hospitality:   X/5  — round((X + X) / 2)
nutrition:     X/5  — [e.g. "lean protein + veg" or "cream/cheese-heavy"]
protein:       X/5  — [e.g. "chicken thighs ~28g/serving" or "veggie-only"]
composite:     X.X/5
```

### 6. Write to `recent-recipes.yaml`

Update or create the ratings block for this recipe. Set `rated_on` to today's date.
Preserve any existing `notes` field. Show what changed.

### 7. Regenerate `recipe-index.md`

After writing, read all entries in `recent-recipes.yaml` that have a `taste` rating.
Compute or verify composite scores. Sort descending by composite (ties broken by
taste, then hospitality). Write the top 25 to `recipe-index.md`:

```markdown
# Top Recipes

_Last updated: YYYY-MM-DD — X recipes scored_

| # | Recipe | Taste | Effort | BfB | Hosp | Nutr | Score |
|---|---|---|---|---|---|---|---|
| 1 | Chicken Carnitas | 5 | 5 | 4 | 5 | 4 | **4.7** |
| 2 | Crispy Gnocchi ✓ | 4 | 5 | 4 | 5 | 3 | **4.2** |

✓ = memorized
```

- Only recipes with a `taste` rating appear
- ✓ suffix if `is_memorized: true`
- Regenerated in full each time (not appended)
