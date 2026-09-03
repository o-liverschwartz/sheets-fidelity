"""Offline. No credentials, no network, no live spreadsheet.

The pure helpers are tested directly, because that is where the bugs actually
are. The four API-touching functions are tested against a fake that records what
it was asked for, which is the part that matters -- whether the right field mask
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
# quote_a1 -- the 400 that eats an afternoon
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
# validate_bounded_range -- refusing the expensive mistake
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad", ["A1:H40", "Sheet1", "Sheet1!A1", "", "!"])
def test_unbounded_or_tabless_ranges_are_refused(bad):
    with pytest.raises(sf.RangeError):
        sf.validate_bounded_range(bad)


def test_a_bounded_range_passes_and_comes_back_quoted():
    assert sf.validate_bounded_range("Q3 Plan!A1:H40") == "'Q3 Plan'!A1:H40"


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class FakeWorksheet:
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
# read_formatting -- the field masks are the whole point
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
    # The structure fetch is allowed; the expensive one must not have happened.
    assert len(sh.fetches) == 1


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
