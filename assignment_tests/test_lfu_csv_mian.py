"""Data-driven tests for cachetools.LFUCache (Mian Dawood).

Test data is read from an external CSV file:
    assignment_tests/data/lfu_cases_mian.csv

CSV columns:
    id, description, maxsize,
    operations         ';'-separated steps: set:<key>, get:<key>, del:<key>, pop
    expected_keys      keys left in the cache, sorted, separated by '|'
    expected_currsize  expected cache.currsize afterwards
    expected_error     exception name raised by the steps (empty = none)

No case relies on a tie between use counts (LFUCache removes an arbitrary key
in that situation), so every result is deterministic.
"""
import builtins
import csv
from pathlib import Path

import pytest

from cachetools import LFUCache

DATA_FILE = Path(__file__).parent / "data" / "lfu_cases_mian.csv"


def load_cases():
    with DATA_FILE.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return [pytest.param(row, id=row["id"]) for row in rows]


def run_operations(cache, operations):
    for step in operations.split(";"):
        action, _, key = step.partition(":")
        if action == "set":
            cache[key] = 1
        elif action == "get":
            cache[key]
        elif action == "del":
            del cache[key]
        elif action == "pop":
            cache.popitem()
        else:
            raise ValueError("unknown operation in CSV: %r" % step)


@pytest.mark.data_driven
@pytest.mark.parametrize("case", load_cases())
def test_lfu_case_from_csv(case):
    cache = LFUCache(int(case["maxsize"]))
    expected_keys = case["expected_keys"].split("|") if case["expected_keys"] else []

    if case["expected_error"]:
        error_type = getattr(builtins, case["expected_error"])
        with pytest.raises(error_type):
            run_operations(cache, case["operations"])
    else:
        run_operations(cache, case["operations"])

    assert sorted(cache) == sorted(expected_keys)
    assert cache.currsize == int(case["expected_currsize"])


def test_csv_has_at_least_four_cases():
    assert len(load_cases()) >= 4
