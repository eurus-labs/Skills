#!/usr/bin/env bash
# GENERATED FILE -- DO NOT EDIT. Regenerate with: python3 tools/build_eval_scaffolds.py
# Recreates fixtures/05-mixed-monorepo in the eval's empty workspace.
set -euo pipefail
mkdir -p '.github/workflows'
cat > '.github/workflows/check.yml' <<'EVAL_FIXTURE_EOF'
name: Check packages
on: [push]
jobs:
  api:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: services/api
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: python -m pip install -e '.[test]'
      - run: python -m pytest
  web:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: apps/web
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '22'
      - run: npm test
EVAL_FIXTURE_EOF
mkdir -p 'apps/web'
cat > 'apps/web/package.json' <<'EVAL_FIXTURE_EOF'
{
  "name": "parcelboard-web",
  "private": true,
  "type": "module",
  "scripts": {
    "test": "node --test"
  }
}
EVAL_FIXTURE_EOF
mkdir -p 'apps/web'
cat > 'apps/web/status.js' <<'EVAL_FIXTURE_EOF'
export function status(parcelId) {
  return { parcelId, state: "queued" };
}
EVAL_FIXTURE_EOF
mkdir -p 'apps/web'
cat > 'apps/web/status.test.js' <<'EVAL_FIXTURE_EOF'
import assert from "node:assert/strict";
import { test } from "node:test";
import { status } from "./status.js";

test("status is queued", () => {
  assert.deepEqual(status("P1"), { parcelId: "P1", state: "queued" });
});
EVAL_FIXTURE_EOF
mkdir -p 'services/api'
cat > 'services/api/parcel.py' <<'EVAL_FIXTURE_EOF'
def status(parcel_id: str) -> dict[str, str]:
    return {"parcel_id": parcel_id, "state": "queued"}
EVAL_FIXTURE_EOF
mkdir -p 'services/api'
cat > 'services/api/pyproject.toml' <<'EVAL_FIXTURE_EOF'
[project]
name = "parcelboard-api"
version = "0.1.0"

[project.optional-dependencies]
test = ["pytest"]

[tool.pytest.ini_options]
testpaths = ["tests"]
EVAL_FIXTURE_EOF
mkdir -p 'services/api/tests'
cat > 'services/api/tests/test_parcel.py' <<'EVAL_FIXTURE_EOF'
from parcel import status


def test_status_is_queued():
    assert status("P1") == {"parcel_id": "P1", "state": "queued"}
EVAL_FIXTURE_EOF
