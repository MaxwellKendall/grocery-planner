# Pinterest Recipe Sync Workflow

## How it works

```
scrape_board.py  →  urls.txt  →  extract_recipe.py  →  recipes/
                                      ↓ on failure
                                  failed.txt
```

### Files

| File | Purpose |
|---|---|
| `urls.txt` | Canonical list of every URL ever seen on the board |
| `failed.txt` | URLs that failed extraction (no JSON-LD, fetch error, bad site) |
| `recipes/*.md` | Successfully extracted recipes |

---

## Deduplication: what's already handled

`extract_recipe.py` already skips a URL if a recipe file with a matching slug exists in `recipes/`. So re-running it against the full `urls.txt` is safe — it will not overwrite or duplicate existing recipes.

## Deduplication: the gaps

1. **New scrape emits all URLs** — `scrape_board.py` outputs the entire board every run. Without filtering, you pass old URLs through `extract_recipe.py` again unnecessarily.
2. **Failed URLs get retried** — `extract_recipe.py` does not read `failed.txt`, so every run retries every URL that previously returned no JSON-LD recipe or a fetch error.

---

## Recommended workflow

### Step 1 — Scrape the board and collect new URLs

```bash
python scripts/scrape_board.py https://www.pinterest.com/USERNAME/BOARD/ \
  | sort > /tmp/board_fresh.txt

# Find URLs not yet in urls.txt
comm -23 /tmp/board_fresh.txt <(sort scripts/urls.txt) > /tmp/new_urls.txt

# Append new URLs to the canonical list
cat /tmp/new_urls.txt >> scripts/urls.txt
sort -u scripts/urls.txt -o scripts/urls.txt

echo "New URLs found: $(wc -l < /tmp/new_urls.txt)"
```

### Step 2 — Extract recipes from new URLs only, skipping known failures

```bash
# Remove any new URLs that previously failed (optional: remove this line to retry failures)
comm -23 <(sort /tmp/new_urls.txt) <(sort scripts/failed.txt) \
  | python scripts/extract_recipe.py --batch
```

That's it. Subsequent runs by your wife adding pins → you re-run both steps → only truly new pins get attempted.

---

## Updating failed.txt

`extract_recipe.py` does not write to `failed.txt` automatically. When a URL fails (you see `no JSON-LD Recipe found` or a fetch error in stderr), add it manually:

```bash
# Capture failures during a batch run
python scripts/extract_recipe.py --batch < /tmp/new_urls.txt 2>&1 \
  | grep -E "^  (error|no JSON-LD)" \
  | sed 's/.*: //' >> scripts/failed.txt
sort -u scripts/failed.txt -o scripts/failed.txt
```

Or after the fact: if you know a URL is junk (an app store link, a TikTok, an index page), just append it to `failed.txt` manually.

---

## Retrying failures

If you want to retry previously failed URLs (e.g., a site was down temporarily):

```bash
python scripts/extract_recipe.py --batch < scripts/failed.txt
```

Remove any that now succeed from `failed.txt` manually.

---

## One-liner for routine use

Once you've done the initial setup, each sync is:

```bash
BOARD="https://www.pinterest.com/USERNAME/BOARD/"

python scripts/scrape_board.py "$BOARD" | sort > /tmp/fresh.txt && \
comm -23 /tmp/fresh.txt <(sort scripts/urls.txt) | tee /tmp/new.txt >> scripts/urls.txt && \
sort -u scripts/urls.txt -o scripts/urls.txt && \
comm -23 <(sort /tmp/new.txt) <(sort scripts/failed.txt) \
  | python scripts/extract_recipe.py --batch
```
