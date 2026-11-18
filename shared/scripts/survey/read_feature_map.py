#!/usr/bin/env python3
"""Read the feature map of a repository that already has one, as a checklist.

    python3 scripts/read_feature_map.py --root . --out .docs-build/feature-map.json

A repository set up with the `verification` plugin's `setup-verification` carries a
project-local `verify-<app>` skill. Its `references/features/` lists the product by what a
user can do, one area per line of `README.md` (`- [checkout](checkout.md) -- owns: ...
-- uses: ...`), with the paths each area `owns:` and `uses:` as globs. That is a second,
independent list of the product's features, and the only one a documentation run can hold
its own coverage against.

It is looked for under `.github/skills/`, `.claude/skills/` and `.agents/skills/` of the
repository being documented, as `verify-*/references/features/*.md`, and **never required**.
With none, this prints `no feature map found` and writes nothing, and the run goes on exactly
as it did before.

What is read is a **checklist and never evidence**. The map was written by an agent and can
be wrong; it adds topics to check and says which files belong to an area, and no sentence of
the manual may cite it. Where its expected behaviour disagrees with the code, the Analyst
records an open question for the user.

Reads the working tree; writes only --out. Standard library only.

Exit codes: 0 read (or none found), 2 input error, 3 internal error.
"""

import argparse
import json
import os
import re
import sys

FEATURE_MAP_VERSION = 1
SKILL_DIRS = (".github/skills", ".claude/skills", ".agents/skills")

INDEX_LINE = re.compile(r"^\s*[-*]\s*\[([^\]]+)\]\(([^)]+)\)(.*)$")
FIELD = re.compile(r"\b(owns|uses):\s*(.*?)(?=\s[—–-]{1,2}\s|\s\b(?:owns|uses):|$)")
BARE_FIELD = re.compile(r"^\s*(?:[-*]\s*)?\*{0,2}(owns|uses)\*{0,2}:\s*(.+)$", re.I)


def fail(message, code=2):
    sys.stderr.write("FAIL  %s\n" % message)
    return code


def globs_of(text):
    """The path globs in one `owns:` or `uses:` value: backticked, else comma-separated."""
    quoted = re.findall(r"`([^`]+)`", text)
    if quoted:
        return [g.strip() for g in quoted if g.strip()]
    return [g.strip() for g in text.split(",") if g.strip() and g.strip() != "-"]


def contained(root_real, path):
    real = os.path.realpath(path)
    return real == root_real or real.startswith(root_real + os.sep)


def read_text(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def parse_index(text):
    """[(name, file, owns, uses)] from the index lines of a features README."""
    entries = []
    lines = text.splitlines()
    for number, line in enumerate(lines):
        match = INDEX_LINE.match(line)
        if not match:
            continue
        # An entry's description wraps onto indented lines; the globs may sit on any of them.
        rest = [match.group(3)]
        for follow in lines[number + 1:]:
            if not follow.startswith((" ", "\t")) or INDEX_LINE.match(follow):
                break
            rest.append(follow.strip())
        joined = " ".join(" ".join(rest).split())
        found = {key: globs_of(value) for key, value in FIELD.findall(joined)}
        entries.append((match.group(1).strip(), match.group(2).strip(),
                        found.get("owns", []), found.get("uses", [])))
    return entries


def parse_area_file(text):
    owns, uses = [], []
    for line in text.splitlines():
        match = BARE_FIELD.match(line)
        if match:
            (owns if match.group(1).lower() == "owns" else uses).extend(
                globs_of(match.group(2)))
    return owns, uses


def read_map(root):
    """The feature map under `root` as a dict, or None when the repository has none."""
    root_real = os.path.realpath(root)
    areas, skills, sources = {}, [], []
    for skills_dir in SKILL_DIRS:
        base = os.path.join(root, *skills_dir.split("/"))
        if not os.path.isdir(base):
            continue
        for skill in sorted(os.listdir(base)):
            features = os.path.join(base, skill, "references", "features")
            if not (skill.startswith("verify-") and os.path.isdir(features)
                    and contained(root_real, features)):
                continue
            files = sorted(n for n in os.listdir(features) if n.endswith(".md")
                           and contained(root_real, os.path.join(features, n)))
            if not files:
                continue
            relative = "%s/%s" % (skills_dir, skill)
            skills.append(relative)
            listed = set()
            if "README.md" in files:
                sources.append("%s/references/features/README.md" % relative)
                for name, target, owns, uses in parse_index(
                        read_text(os.path.join(features, "README.md"))):
                    listed.add(os.path.basename(target))
                    area = areas.setdefault(name, {"name": name, "skill": relative,
                                                   "file": target, "owns": [], "uses": []})
                    own_file = os.path.join(features, os.path.basename(target))
                    extra_owns, extra_uses = ([], [])
                    if os.path.isfile(own_file) and contained(root_real, own_file):
                        extra_owns, extra_uses = parse_area_file(read_text(own_file))
                    for key, values in (("owns", owns + extra_owns),
                                        ("uses", uses + extra_uses)):
                        area[key].extend(v for v in values if v not in area[key])
            for name in files:
                if name == "README.md" or name in listed:
                    continue
                owns, uses = parse_area_file(read_text(os.path.join(features, name)))
                if owns or uses:
                    stem = name[:-3]
                    area = areas.setdefault(stem, {"name": stem, "skill": relative,
                                                   "file": name, "owns": [], "uses": []})
                    area["owns"].extend(v for v in owns if v not in area["owns"])
                    area["uses"].extend(v for v in uses if v not in area["uses"])
                    sources.append("%s/references/features/%s" % (relative, name))
    if not areas:
        return None
    return {"feature_map_version": FEATURE_MAP_VERSION, "skills": skills,
            "sources": sorted(sources),
            "areas": sorted(areas.values(), key=lambda a: a["name"])}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=".", help="the repository being documented")
    parser.add_argument("--out", default=".docs-build/feature-map.json")
    args = parser.parse_args()
    if not os.path.isdir(args.root):
        return fail("no such directory: %s" % args.root)

    found = read_map(args.root)
    if found is None:
        print("no feature map found")
        # A map that has since been deleted must not keep adding topics from an earlier run.
        if os.path.isfile(args.out):
            os.remove(args.out)
            print("removed %s, left by an earlier run" % args.out)
        return 0

    directory = os.path.dirname(os.path.abspath(args.out))
    os.makedirs(directory, exist_ok=True)
    temporary = args.out + ".tmp"
    with open(temporary, "w", encoding="utf-8") as fh:
        json.dump(found, fh, indent=1, sort_keys=True)
        fh.write("\n")
    os.replace(temporary, args.out)
    print("feature map: %d area(s) from %s" % (len(found["areas"]),
                                               ", ".join(found["skills"])))
    for area in found["areas"]:
        print("  %-24s owns %d, uses %d" % (area["name"], len(area["owns"]),
                                            len(area["uses"])))
    print("wrote %s -- a checklist to read the scope against, never evidence to cite"
          % args.out)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write("ERROR %s\n" % exc)
        sys.exit(3)
