"""Offline. No credentials, no network, no live spreadsheet.

The pure helpers are tested directly, because that is where the bugs actually
are. The four API-touching functions are tested against a fake that records what
it was asked for, which is the part that matters: whether the right field mask
and the right options went out.
"""
import pytest

import sheets_fidelity as sf


# ---------------------------------------------------------------------------
# col_letter
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("n,expected", [
    (1, "A"), (2, "B"), (26, "Z"), (27, "AA"), (28, "AB"),
    (52, "AZ"), (53, "BA"), (702, "ZZ"), (703, "AAA"),
])
def test_col_letter(n, expected):
    assert sf.col_letter(n) == expected


def test_col_letter_is_one_based():
    with pytest.raises(ValueError):
        sf.col_letter(0)


# ---------------------------------------------------------------------------
# quote_a1: the 400 that eats an afternoon
# ---------------------------------------------------------------------------

def test_a_tab_with_a_space_gets_quoted():
    assert sf.quote_a1("Q3 Plan!A1:H40") == "'Q3 Plan'!A1:H40"


def test_a_tab_with_punctuation_gets_quoted():
    assert sf.quote_a1("Sales (EU)!A1:B2") == "'Sales (EU)'!A1:B2"


def test_an_apostrophe_in_a_tab_name_is_doubled():
    # The one that looks fine in testing and breaks on a real user's tab.
    assert sf.quote_a1("Bob's Tab!A1:B2") == "'Bob''s Tab'!A1:B2"


def test_already_quoted_is_left_alone():
    assert sf.quote_a1("'Q3 Plan'!A1:H40") == "'Q3 Plan'!A1:H40"


def test_a_range_with_no_tab_is_left_alone():
    assert sf.quote_a1("A1:H40") == "A1:H40"


def test_quoting_is_idempotent():
    once = sf.quote_a1("Q3 Plan!A1:B2")
    assert sf.quote_a1(once) == once


# ---------------------------------------------------------------------------
# validate_bounded_range: refusing the expensive mistake
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad", [
    "A1:H40", "Sheet1", "", "!", "!A1:B2",
    "Sheet1!A:A", "Sheet1!1:1", "Sheet1!A1:Z", "Plan: Q3",
    "Sheet1!$A:$A", "Sheet1!$A$1:$Z",
])
def test_unbounded_or_tabless_ranges_are_refused(bad):
    with pytest.raises(sf.RangeError):
        sf.validate_bounded_range(bad)


@pytest.mark.parametrize("good", [
    "Sheet1!A1", "Plan: Q3!A1:B2", "'Wow!'!A1:B2",
    "Sheet1!$A$1:$B$2", "Sheet1!$A1:B$2", "Sheet1!$C$3",
])
def test_a_single_cell_or_a_colon_in_the_tab_name_is_fine(good):
    assert sf.validate_bounded_range(good)


def test_a_bounded_range_passes_and_comes_back_quoted():
    assert sf.validate_bounded_range("Q3 Plan!A1:H40") == "'Q3 Plan'!A1:H40"


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class FakeWorksheet:
    title = "Q3 Plan"

    def __init__(self):
        self.calls = []

    def get(self, cell_range, value_render_option=None):
        self.calls.append(("get", cell_range, value_render_option))
        return [["a"]]

    def get_all_values(self, value_render_option=None):
        self.calls.append(("get_all_values", None, value_render_option))
        return [["a"]]

    def update(self, values=None, range_name=None, value_input_option=None):
        self.calls.append(("update", range_name, value_input_option, values))


class FakeSpreadsheet:
    def __init__(self):
        self.fetches = []
        self.updates = []

    def fetch_sheet_metadata(self, params=None):
        self.fetches.append(params or {})
        return {"ok": True}

    def batch_update(self, body):
        self.updates.append(body)


# ---------------------------------------------------------------------------
# read_values
# ---------------------------------------------------------------------------

def test_render_option_is_passed_through():
    ws = FakeWorksheet()
    sf.read_values(ws, "A1:B2", render="UNFORMATTED_VALUE")
    assert ws.calls == [("get", "A1:B2", "UNFORMATTED_VALUE")]


def test_no_range_reads_the_whole_tab():
    ws = FakeWorksheet()
    sf.read_values(ws)
    assert ws.calls[0][0] == "get_all_values"


def test_an_invented_render_option_is_refused_before_the_call():
    ws = FakeWorksheet()
    with pytest.raises(ValueError):
        sf.read_values(ws, "A1:B2", render="RAW_VALUE")
    assert ws.calls == []


# ---------------------------------------------------------------------------
# write_values
# ---------------------------------------------------------------------------

def test_write_defaults_to_user_entered():
    ws = FakeWorksheet()
    sf.write_values(ws, "B2:B3", [[1], [2]])
    assert ws.calls == [("update", "B2:B3", "USER_ENTERED", [[1], [2]])]


def test_raw_is_available_for_values_that_must_not_be_coerced():
    ws = FakeWorksheet()
    sf.write_values(ws, "A1", [["0012"]], value_input_option="RAW")
    assert ws.calls[0][2] == "RAW"


def test_an_invented_input_option_is_refused_before_the_call():
    ws = FakeWorksheet()
    with pytest.raises(ValueError):
        sf.write_values(ws, "A1", [["x"]], value_input_option="MAGIC")
    assert ws.calls == []


# ---------------------------------------------------------------------------
# read_formatting: the field masks are the whole point
# ---------------------------------------------------------------------------

def test_structure_only_by_default():
    sh = FakeSpreadsheet()
    out = sf.read_formatting(sh)
    assert list(out) == ["structure"]
    assert len(sh.fetches) == 1
    assert sh.fetches[0]["fields"] == sf.FIELDS_STRUCTURE
    # The expensive switch must not be on.
    assert "includeGridData" not in sh.fetches[0]


def test_structure_mask_covers_what_a_person_would_miss():
    # These are the ones that silently vanish in a naive sync.
    for field in ["conditionalFormats", "protectedRanges", "bandedRanges",
                  "merges", "rowGroups", "columnGroups", "namedRanges"]:
        assert field in sf.FIELDS_STRUCTURE


def test_a_range_adds_the_cell_fetch_and_quotes_the_tab():
    sh = FakeSpreadsheet()
    out = sf.read_formatting(sh, "Q3 Plan!A1:H40")
    assert list(out) == ["structure", "cells"]
    cells = sh.fetches[1]
    assert cells["fields"] == sf.FIELDS_CELLS
    assert cells["ranges"] == "'Q3 Plan'!A1:H40"
    assert cells["includeGridData"] == "true"


def test_an_unbounded_range_never_reaches_the_network():
    sh = FakeSpreadsheet()
    with pytest.raises(sf.RangeError):
        sf.read_formatting(sh, "Sheet1")
    assert sh.fetches == []


# ---------------------------------------------------------------------------
# batch_format
# ---------------------------------------------------------------------------

def test_batch_format_sends_the_requests():
    sh = FakeSpreadsheet()
    reqs = [{"repeatCell": {}}, {"updateSheetProperties": {}}]
    assert sf.batch_format(sh, reqs) == 2
    assert sh.updates == [{"requests": reqs}]


def test_an_empty_batch_is_not_a_network_call():
    sh = FakeSpreadsheet()
    assert sf.batch_format(sh, []) == 0
    assert sh.updates == []


# ---------------------------------------------------------------------------
# tab-qualified ranges on the value path
# ---------------------------------------------------------------------------

def test_a_tab_qualified_range_is_reduced_to_its_span():
    ws = FakeWorksheet()
    sf.read_values(ws, "Q3 Plan!C2:C40")
    sf.write_values(ws, "'Q3 Plan'!C2:C3", [[1], [2]])
    assert ws.calls[0][1] == "C2:C40"
    assert ws.calls[1][1] == "C2:C3"


def test_a_range_naming_another_tab_is_refused_before_the_call():
    ws = FakeWorksheet()
    with pytest.raises(sf.RangeError):
        sf.read_values(ws, "Other!A1:B2")
    assert ws.calls == []


# ---------------------------------------------------------------------------
# masks cover what the README says they cover
# ---------------------------------------------------------------------------

def test_cell_mask_carries_the_content_a_naive_write_loses():
    for field in ["textFormatRuns", "note", "hyperlink", "hiddenByUser", "dataValidation"]:
        assert field in sf.FIELDS_CELLS


def test_structure_mask_carries_filters():
    for field in ["basicFilter", "filterViews"]:
        assert field in sf.FIELDS_STRUCTURE


# ---------------------------------------------------------------------------
# diff_structure
# ---------------------------------------------------------------------------

def _snap(**kw):
    props = {"title": "Plan", "gridProperties": {"frozenRowCount": kw.pop("frozen", 0)}}
    return {"sheets": [{"properties": props, **kw}]}


def test_nothing_lost_is_an_empty_diff():
    a = _snap(merges=[{}], frozen=1)
    assert sf.diff_structure(a, a) == {}


def test_lost_merges_and_frozen_row_are_reported():
    before = _snap(merges=[{}, {}], conditionalFormats=[{}], frozen=1)
    after = _snap(conditionalFormats=[{}])
    assert sf.diff_structure(before, after) == {
        "Plan": {"merges": (2, 0), "frozenRows": (1, 0)}}


def test_a_vanished_tab_is_reported():
    assert sf.diff_structure(_snap(), {"sheets": []}) == {"Plan": {"tab": (1, 0)}}


# ---------------------------------------------------------------------------
# find_dead_formulas
# ---------------------------------------------------------------------------

class RenderWorksheet(FakeWorksheet):
    def __init__(self, formula, unformatted):
        super().__init__()
        self.by_render = {"FORMULA": formula, "UNFORMATTED_VALUE": unformatted}

    def get(self, cell_range, value_render_option=None):
        return self.by_render[value_render_option]


def test_dead_formula_is_found_and_blank_rows_do_not_crash():
    ws = RenderWorksheet(
        formula=[["=SUM(A1:A9)"], [], ["=B2"], ["plain"]],
        unformatted=[[45], [], ["=B2"], ["plain"]],
    )
    assert sf.find_dead_formulas(ws, "C2:C5") == ["C4"]


def test_dead_formulas_accept_an_absolute_range():
    ws = RenderWorksheet(formula=[["=B2"]], unformatted=[["=B2"]])
    assert sf.find_dead_formulas(ws, "$C$2:$C$2") == ["C2"]


def test_an_absolute_range_reaches_the_cell_fetch():
    sh = FakeSpreadsheet()
    sf.read_formatting(sh, "Sheet1!$A$1:$B$2")
    assert sh.fetches[1]["ranges"] == "'Sheet1'!$A$1:$B$2"


# ---------------------------------------------------------------------------
# The round trip the README leads with: read FORMULA, write USER_ENTERED
# ---------------------------------------------------------------------------

def test_a_formula_read_as_formula_goes_back_as_a_formula():
    ws = RenderWorksheet(formula=[["=SUM(A3:B3)"]], unformatted=[[30]])
    ws.calls = []
    block = sf.read_values(ws, "C3", render="FORMULA")
    sf.write_values(ws, "C3", block)
    assert ws.calls == [("update", "C3", "USER_ENTERED", [["=SUM(A3:B3)"]])]


# ---------------------------------------------------------------------------
# What gspread itself sends. The fakes above take a range verbatim, which is
# how the doubled tab name got through. This one goes through a real
# gspread.Worksheet and records the URL range it would request.
# ---------------------------------------------------------------------------

from gspread.http_client import HTTPClient


class RecordingClient(HTTPClient):
    def __init__(self):   # no auth, no session
        self.ranges = []

    def values_get(self, id, range, params=None):
        self.ranges.append(range)
        return {"range": range, "majorDimension": "ROWS", "values": [["x"]]}

    def values_update(self, id, range, params=None, body=None):
        self.ranges.append(range)
        return {"updatedRange": range}


def _real_worksheet():
    import gspread
    client = RecordingClient()
    ws = gspread.Worksheet(
        spreadsheet=None,
        properties={"sheetId": 0, "title": "Q3 Plan", "index": 0},
        spreadsheet_id="test",
        client=client,
    )
    return ws, client


def test_gspread_sends_the_tab_name_once():
    ws, client = _real_worksheet()
    sf.read_values(ws, "Q3 Plan!C2:C40")
    sf.write_values(ws, "'Q3 Plan'!C2:C3", [[1], [2]])
    assert client.ranges == ["'Q3 Plan'!C2:C40", "'Q3 Plan'!C2:C3"]


# ---------------------------------------------------------------------------
# Repo hygiene: one version everywhere, build output ignored
# ---------------------------------------------------------------------------

import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_one_version_everywhere():
    pyproject = re.search(r'^version = "([^"]+)"', (ROOT / "pyproject.toml").read_text(), re.M)
    plugin = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())
    assert pyproject.group(1) == plugin["version"] == sf.__version__


def test_build_output_is_ignored():
    ignored = (ROOT / ".gitignore").read_text().split()
    for entry in ["*.egg-info/", "build/", "dist/"]:
        assert entry in ignored
