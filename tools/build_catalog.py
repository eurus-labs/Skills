#!/usr/bin/env python3
"""Build catalog.json: every plugin, its skills, its eval cases and its archived eval scores, as one JSON file.

The VS Code extension (extensions/vscode/) and, later, a public web page read this file. It is built from the
marketplace manifest, each plugin's manifest and eval cases, and the tracked `plugins/*/evals/archive/` runs, so
a clean checkout gives the same bytes on every machine. It holds no generation time.

    python3 tools/build_catalog.py           # write catalog.json at the repository root
    python3 tools/build_catalog.py --check   # write nothing; exit 1 when catalog.json is out of date

The scoring is the eval board's (`build_eval_board.catalog`, `load_results`, `trusted`), not a second copy:
this file only reshapes what the board already knows. `tools/skill_manager.py` serves the same schema from
`GET /api/catalog`, with the runs in the git-ignored `results/` as well.

`tools/featured.json` ({"plugin", "note", "text"}) names the plugin the store's featured card shows. A name that
is not in the marketplace fails the build.

Standard library only. No network call. Writes only catalog.json.
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_eval_board as board  # noqa: E402

REPO = board.REPO
SCHEMA_VERSION = 1
SOURCE = "eurus-labs/Skills"
OUTPUT = "catalog.json"
FEATURED = os.path.join("tools", "featured.json")
MARKETPLACE_FILE = os.path.join(".github", "plugin", "marketplace.json")
FEATURED_KEYS = ("plugin", "note", "text")


class CatalogError(Exception):
    """The inputs cannot make a catalog; the message says which and why."""


def read_json(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError) as exc:
        raise CatalogError("cannot read %s: %s" % (path, exc))


def featured_entry(repo, names):
    path = os.path.join(repo, FEATURED)
    if not os.path.isfile(path):
        return None
    doc = read_json(path)
    if not isinstance(doc, dict) or any(not isinstance(doc.get(k), str) or not doc[k] for k in FEATURED_KEYS):
        raise CatalogError("%s must be an object with the non-empty text keys %s" % (FEATURED, ", ".join(FEATURED_KEYS)))
    if doc["plugin"] not in names:
        raise CatalogError("%s names plugin '%s', which is not in the marketplace" % (FEATURED, doc["plugin"]))
    return {k: doc[k] for k in FEATURED_KEYS}


def kind_of(case):
    """fires, quiet or behavior. A trigger case that names a skill to call is `fires`, whatever else it forbids."""
    if case["kind"] == "behavior":
        return "behavior"
    return "fires" if case["fires"] or not case["quiet"] else "quiet"


def result_paths(repo, include_local):
    paths = board.result_files(repo)
    if include_local:
        return paths
    return [p for p in paths if board.ARCHIVE_DIR.search(os.path.abspath(p))]


def mean(values):
    return round(sum(values) / len(values), 2)


def skill_evals(plugin, skill, history, hosts):
    """{"cases": n tied to the skill, "hosts": {host: {cases, score, latest}}} from each case's newest trusted run."""
    tied = [c["name"] for c in plugin["cases"] if skill in c["skills"]]
    found = {}
    for host in hosts:
        picked = []
        for name in tied:
            for run in history.get("%s/%s" % (plugin["name"], name), []):  # newest first
                if run["host"] == host and board.trusted(run):
                    picked.append(run)
                    break
        if picked:
            found[host] = {"cases": len(picked), "score": mean([r["score"] for r in picked]),
                           "latest": max(r["stamp"] for r in picked)}
    return {"cases": len(tied), "hosts": found}


def case_entry(plugin, case, history, hosts):
    latest = {}
    for host in hosts:
        for run in history.get("%s/%s" % (plugin, case["name"]), []):
            if run["host"] == host:
                latest[host] = {"stamp": run["stamp"], "runs": run["runs"],
                                "score": None if run["score"] is None else round(run["score"], 2),
                                "trusted": board.trusted(run)}
                break
    return {"name": case["name"], "kind": kind_of(case), "skills": list(case["skills"]),
            "description": case["description"], "latest": latest}


def runs_of(plugin, history):
    """One entry per result file of the plugin, oldest first: the mean of its non-null case scores."""
    files = {}
    for key, runs in history.items():
        if key.split("/", 1)[0] != plugin:
            continue
        for run in runs:
            entry = files.setdefault(run["stamp"], {"host": run["host"], "scores": []})
            if run["score"] is not None:
                entry["scores"].append(run["score"])
    return [{"stamp": stamp, "host": entry["host"], "score": mean(entry["scores"]) if entry["scores"] else None,
             "cases": len(entry["scores"])} for stamp, entry in sorted(files.items())]


def build(repo=REPO, include_local=False):
    """The catalog as a dict. `include_local` also reads the git-ignored results/ folders (the skill manager)."""
    market = read_json(os.path.join(repo, MARKETPLACE_FILE))
    listed = market.get("plugins") or []
    names = [p["name"] for p in listed]
    from_board = {p["name"]: p for p in board.catalog(repo)}
    history = board.load_results(result_paths(repo, include_local))
    hosts = [h["id"] for h in board.HOSTS]
    plugins = []
    for entry in listed:
        name = entry["name"]
        if name not in from_board:
            raise CatalogError("the marketplace lists '%s', but plugins/%s has no skills folder" % (name, name))
        found = from_board[name]
        skills = [{"name": s[0], "description": s[1], "evals": skill_evals(found, s[0], history, hosts)}
                  for s in found["skills"]]
        plugins.append({"name": name, "version": entry.get("version"), "description": entry.get("description", ""),
                        "skills": skills, "cases": [case_entry(name, c, history, hosts) for c in found["cases"]],
                        "runs": runs_of(name, history)})
    meta = market.get("metadata") or {}
    return {"schemaVersion": SCHEMA_VERSION,
            "marketplace": {"name": market.get("name"), "version": meta.get("version"), "source": SOURCE},
            "hosts": [{"id": h["id"], "label": h["label"]} for h in board.HOSTS],
            "featured": featured_entry(repo, names),
            "plugins": plugins}


def render(catalog):
    """The exact bytes of catalog.json: sorted keys, 2-space indentation, a final newline."""
    return json.dumps(catalog, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main(argv=None, repo=REPO):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--check", action="store_true",
                        help="write nothing; exit 1 when catalog.json is out of date")
    args = parser.parse_args(argv)
    try:
        text = render(build(repo))
    except CatalogError as exc:
        print("build_catalog: %s" % exc, file=sys.stderr)
        return 1
    path = os.path.join(repo, OUTPUT)
    if args.check:
        try:
            with open(path, encoding="utf-8", newline="") as fh:
                current = fh.read()
        except OSError:
            current = None
        if current == text:
            print("catalog.json is up to date")
            return 0
        print("catalog.json is %s. Run: python3 tools/build_catalog.py" % ("missing" if current is None else "out of date"))
        return 1
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print("wrote %s: %d plugin(s), %d bytes" % (OUTPUT, len(json.loads(text)["plugins"]), len(text.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
