---
name: process-receipt
description: Convert pending HEIC/JPG/PNG receipt photos in reciepts/ to readable JPEGs, then reconcile them against shopping lists (REVIEW mode).
user-invocable: true
---

# Process Receipt Skill

Converts any pending receipt images in `reciepts/` to readable JPEGs, then runs full receipt reconciliation per the REVIEW mode in CLAUDE.md.

## Usage

```
/process-receipt
```

## Procedure

1. **Run the conversion script** — execute `bash scripts/convert-receipt-heic.sh` from the repo root. It prints one output path per converted file.
2. **Read each output path** — use the Read tool on each printed path to view the receipt image.
3. **Reconcile** — follow the REVIEW mode steps in CLAUDE.md:
   - Extract all line items (item, qty, price paid, store, date)
   - Update `prices.json` with actual prices (store-keyed, date-stamped)
   - Compare against the shopping list for that date in `lists/` if one exists; flag unplanned and skipped items
   - Update `pantry.yaml` with purchased items
   - Update `profile.yaml` (monthly actuals, trip history, insights)
   - Move the original receipt file from `reciepts/` to `reciepts/processed/`
4. **Output** the reconciliation summary in the format defined in CLAUDE.md
