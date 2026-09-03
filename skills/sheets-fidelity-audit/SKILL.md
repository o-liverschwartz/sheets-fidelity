---
name: sheets-fidelity-audit
description: Audits a Google Sheets workflow for read-store-write fidelity. Use when a sheet imports correctly but writes back wrong, or when values, formulas, formatting, notes, groups, hidden rows, frozen panes, banding, or conditional rules may be drifting.
disable-model-invocation: true
---

Run a full Google Sheets fidelity audit.

Your goal is to find exactly where fidelity is being lost between:
1. reading from Google Sheets
2. storing in app/database/template state
3. writing back to Google Sheets

Do not jump straight to patching. Prove the failure layer first.

## Audit procedure

### Step 1: Define the concrete failing example
Pick 1-3 specific examples, not abstractions:
- one value/formula case
- one formatting case
- one structure/layout case if relevant

Examples:
- a formula cell that becomes a static value
- a bold/italic/indented label that pushes back wrong
- a grouped or hidden row that loses state
- a merged header that disappears
- a conditional format or banded range that gets deleted or overwritten

### Step 2: Capture the read layer
For each example, show exactly what the Sheets API returns.

Prefer a compact but real payload view containing:
- `userEnteredValue`
- `effectiveValue`
- `formattedValue`
- `userEnteredFormat`
- `effectiveFormat`
- `textFormatRuns`
- `note`
- `hyperlink`
- `dataValidation`
- row/column metadata if relevant
- group / sheet-level metadata if relevant

Do not summarize vaguely. Show the actual fields that matter.

### Step 3: Capture the stored layer
Show exactly what the app persists:
- database columns
- JSON blobs
- in-memory state
- template records
- layout config
- request builders' inputs

Be explicit about fields that are:
- preserved exactly
- normalized
- collapsed to booleans
- dropped completely

### Step 4: Capture the write layer
Show the exact outbound write operations:
- `spreadsheets.values.batchUpdate` payloads
- `repeatCell`
- `updateBorders`
- `updateDimensionProperties`
- `updateSheetProperties`
- `mergeCells` / `unmergeCells`
- group add/update/delete requests
- banding requests
- conditional format requests
- protected range requests

List:
- range
- API method
- field mask
- order of execution
- possible overlap

### Step 5: Produce the loss map
Create this table:

| Feature | Read from sheet? | Stored? | Written? | Preserved / Lossy / Hardcoded / Dropped? |

Include at minimum:
- values
- formulas
- displayed text
- number format
- font family
- font size
- bold
- italic
- font color
- background color
- borders by side
- border style
- border color
- alignment
- wrap strategy
- padding / indent
- note
- hyperlink
- text runs
- data validation
- row height
- column width
- hidden rows / columns
- row groups / column groups
- frozen rows / columns
- merges
- filters
- protected ranges
- banding
- conditional formatting

### Step 6: Call out overlap and merge behavior
Pay special attention to:
- broad `repeatCell` requests
- update masks that are too wide
- values writes followed by formatting writes
- formatting writes followed by rule/layout writes
- deletions that happen before replacement payloads exist
- row-wide writes that unintentionally affect formula/data columns

### Step 7: Classify the system
Say which of these the workflow really is:

A. **Exact preservation**
B. **Standardized reconstruction**
C. **Hybrid ownership**
D. **Unclear / inconsistent**

Do not be polite if the system is actually inconsistent.

### Step 8: Recommend a safe next move
Offer only one primary recommendation, chosen from:
- freeze writes and switch to safe mode
- narrow writes to owned surfaces only
- add missing stored metadata
- split content sync from layout sync
- redesign ownership model
- standardize deliberately instead of pretending fidelity

## Required output structure

Use this exact section order:

1. **Failure summary**
2. **Concrete examples audited**
3. **Read layer**
4. **Stored layer**
5. **Write layer**
6. **Fidelity table**
7. **Overlapping / destructive request risks**
8. **Actual ownership model today**
9. **Recommended next move**
10. **Open assumptions not yet proven**

## Behavior rules

- Do not patch code until the audit is complete.
- Do not say "looks fine" without evidence.
- Do not confuse structural bugs with fidelity bugs.
- If the write layer is reconstructing instead of preserving, say so directly.
- If the schema is too weak for exact fidelity, say so directly.
- If a safer temporary mode is warranted, recommend it.
