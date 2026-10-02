# Live check

The test suite never talks to Google. This does, once, against a scratch sheet you own. It checks the README's central claim (a `FORMULA` read written back stays a formula, an `UNFORMATTED_VALUE` read written back does not), the premise of `find_dead_formulas`, and that Google accepts the field masks in `read_formatting`.

It writes to rows 1 to 3 of the first tab. Use a new, empty sheet.

## Steps

1. Make a blank Google Sheet. Copy its id from the URL (the part between `/d/` and `/edit`).
2. From a clone, with the package installed (`pip install -e ".[dev]"`):

```
SHEET_ID=paste-the-id-here python docs/live_check.py
```

The script uses your existing application default credentials with the Sheets scope. It does not log in or open a browser. If you would rather use gspread's own OAuth flow, swap the two `creds` lines for `gc = gspread.oauth()`.

3. Compare the output with the expected block below. Then delete the scratch sheet.

## Expected output

```
FORMULA            [[30], ['=SUM(A2:B2)'], ['=SUM(A3:B3)']]
UNFORMATTED_VALUE  [[30], [35], ['=SUM(A3:B3)']]
dead formulas      ['C3']
structure fields   ok
cell fields        ok
```

What each line means:

- Row 1 was read with `UNFORMATTED_VALUE` and written back, so C1 is the constant 30 and did not move when A1 became 15. If `FORMULA` shows it as `'30'`, a string, the check still passes, because C1 no longer holds `=SUM(A1:B1)`.
- Row 2 was read with `FORMULA` and written back, so C2 is still `=SUM(A2:B2)` and now shows 35.
- Row 3 was written as text with `RAW`. It reads `=SUM(A3:B3)` under both renders, which is what `find_dead_formulas` relies on.
- The last two lines mean Google accepted every path in `FIELDS_STRUCTURE` and `FIELDS_CELLS`. A typo in a mask comes back as a 400 and the script stops there.

If rows 1 or 2 come back different, the README's first section is wrong and needs changing before anything is tagged. If row 3 differs, `find_dead_formulas` is wrong.
