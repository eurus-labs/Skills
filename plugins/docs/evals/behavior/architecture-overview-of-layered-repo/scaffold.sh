#!/usr/bin/env bash
# GENERATED FILE -- DO NOT EDIT. Regenerate with: python3 tools/build_eval_scaffolds.py
# Recreates tests/contracts/layered-repo in the eval's empty workspace.
set -euo pipefail
cat > 'README.md' <<'EVAL_FIXTURE_EOF'
# orderlog

A command-line tool that records orders and reports on them.

It exists because the team needed order history that outlives a spreadsheet, without
running a database server. Not a general accounting package: it stores orders and
prints them back.
EVAL_FIXTURE_EOF
cat > 'pyproject.toml' <<'EVAL_FIXTURE_EOF'
[project]
name = "orderlog"
version = "0.1.0"
requires-python = ">=3.9"

[project.scripts]
orderlog = "app.api.cli:main"
EVAL_FIXTURE_EOF
mkdir -p '.github/workflows'
cat > '.github/workflows/ci.yml' <<'EVAL_FIXTURE_EOF'
name: ci
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: python3 -m pytest
EVAL_FIXTURE_EOF
mkdir -p 'src/app'
: > 'src/app/__init__.py'
mkdir -p 'src/app/api'
: > 'src/app/api/__init__.py'
mkdir -p 'src/app/api'
cat > 'src/app/api/cli.py' <<'EVAL_FIXTURE_EOF'
"""Command line entry point."""

import sys

from app.core.service import OrderService


def main():
    service = OrderService()
    service.record(sys.argv[1:])
    return 0


if __name__ == "__main__":
    sys.exit(main())
EVAL_FIXTURE_EOF
mkdir -p 'src/app/api'
cat > 'src/app/api/http.py' <<'EVAL_FIXTURE_EOF'
"""HTTP boundary. Validates input before anything else sees it."""

from app.core.service import OrderService


class Handler:
    def __init__(self):
        self.service = OrderService()

    def post(self, body):
        if "sku" not in body:
            raise ValueError("sku is required")
        return self.service.record([body["sku"]])
EVAL_FIXTURE_EOF
mkdir -p 'src/app/core'
: > 'src/app/core/__init__.py'
mkdir -p 'src/app/core'
cat > 'src/app/core/models.py' <<'EVAL_FIXTURE_EOF'
"""Domain types."""


class Record:
    key = 0


class Order(Record):
    def __init__(self, sku):
        self.sku = sku

    def total(self):
        return len(self.sku)
EVAL_FIXTURE_EOF
mkdir -p 'src/app/core'
cat > 'src/app/core/service.py' <<'EVAL_FIXTURE_EOF'
"""Application workflow. Owns no storage of its own."""

from app.core.models import Order
from app.infra.store import Store


class OrderService:
    def __init__(self):
        self.store = Store()

    def record(self, skus):
        for sku in skus:
            self.store.put(Order(sku))
        return len(skus)
EVAL_FIXTURE_EOF
mkdir -p 'src/app/infra'
: > 'src/app/infra/__init__.py'
mkdir -p 'src/app/infra'
cat > 'src/app/infra/config.py' <<'EVAL_FIXTURE_EOF'
"""Configuration loading."""

import os


def load():
    return {"path": os.environ.get("ORDERLOG_PATH", "orders.json")}
EVAL_FIXTURE_EOF
mkdir -p 'src/app/infra'
cat > 'src/app/infra/store.py' <<'EVAL_FIXTURE_EOF'
"""Persistence. Keeps orders in memory until flushed."""

from app.infra.config import load


class Store:
    def __init__(self):
        self.settings = load()
        self.rows = []

    def put(self, order):
        self.rows.append(order)
        return len(self.rows)
EVAL_FIXTURE_EOF
