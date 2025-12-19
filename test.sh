#!/bin/bash
set -euo pipefail

MODE="${1:-new}"

case "${MODE}" in
  base)
    echo "Running base mode: existing tests to verify no regressions..."
    pytest tests/ --ignore=tests/test_ttl_get.py -q
    ;;
  new)
    echo "Running new mode: tests for new functionality..."
    pytest tests/test_ttl_get.py -v
    ;;
  *)
    echo "Usage: ./test.sh [base|new]"
    echo ""
    echo "  base - Run pre-existing test suite (legacy tests that verify original behavior)"
    echo "  new  - Run only new tests introduced by this patch (default)"
    exit 1
    ;;
esac
