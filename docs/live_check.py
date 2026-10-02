"""Run against a scratch sheet you own. See docs/LIVE-CHECK.md."""
import os

import google.auth
import gspread

from sheets_fidelity import find_dead_formulas, read_formatting, read_values, write_values

creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/spreadsheets"])
gc = gspread.authorize(creds)
sh = gc.open_by_key(os.environ["SHEET_ID"])
ws = sh.sheet1

# Rows 1 and 2: a live formula. Row 3: the same text, stored as text.
write_values(ws, "A1:C2", [[10, 20, "=SUM(A1:B1)"], [10, 20, "=SUM(A2:B2)"]])
write_values(ws, "A3:C3", [[10, 20, "=SUM(A3:B3)"]], value_input_option="RAW")

# Round trip C1 through UNFORMATTED_VALUE and C2 through FORMULA.
write_values(ws, "C1", read_values(ws, "C1", render="UNFORMATTED_VALUE"))
write_values(ws, "C2", read_values(ws, "C2", render="FORMULA"))

# Change the inputs. A live formula moves, a constant does not.
write_values(ws, "A1:A2", [[15], [15]])

print("FORMULA           ", read_values(ws, "C1:C3", render="FORMULA"))
print("UNFORMATTED_VALUE ", read_values(ws, "C1:C3", render="UNFORMATTED_VALUE"))
print("dead formulas     ", find_dead_formulas(ws, "C1:C3"))

out = read_formatting(sh)
print("structure fields  ", "ok" if out["structure"].get("sheets") else out)
out = read_formatting(sh, "%s!$A$1:$C$3" % ws.title)
print("cell fields       ", "ok" if out["cells"].get("sheets") else out)
