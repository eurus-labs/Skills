#!/usr/bin/env python3
"""Keep `claude plugin eval` results in the repository, with local paths scrubbed.

`claude plugin eval` writes `aggregate-result.json` and `report.html` to
`plugins/<plugin>/evals/results/<timestamp>/`, which is git-ignored. This tool copies those two files to
`plugins/<plugin>/evals/archive/<timestamp>/`, which is tracked, after removing what must not be committed:

- every absolute local path (`/root/...`, `/home/<x>/...`, `/Users/<x>/...`, `/tmp/...`, `/var/folders/...`,
  `C:\\Users\\<x>\\...`, and this repository's own path) becomes `<local>`; a path inside this repository keeps
  its part below the repository root. `tracePath` becomes null, because the trace is not archived;
- a file that still matches a secret pattern, is over 5 MB, or belongs to an unknown plugin is refused.

Transcripts (`*.jsonl`, `*.md`) are never copied.

    python3 tools/archive_eval_results.py <source>...      # archive runs
    python3 tools/archive_eval_results.py --replace <src>  # overwrite an archived run whose content differs
    python3 tools/archive_eval_results.py --check          # verify what is already archived; writes nothing

A source is a `results/<timestamp>/` folder, an `aggregate-result.json`, or a folder that holds
`plugins/*/evals/results/*` (an unpacked bundle). Exit 0 on success, 1 when something is refused or `--check`
finds an offender, 2 on a usage error. A refusal names the file and the rule, never the text that matched.

Standard library only. No network call. Reads `git config user.email` (read-only) to refuse that address.
Writes only under `plugins/*/evals/archive/`.
"""

import argparse
import glob
import html
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MAX_BYTES = 5 * 1024 * 1024
FILES = ("aggregate-result.json", "report.html")
PLACEHOLDER = "<local>"
NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
PLUGIN_NAME = re.compile(r"^[a-z0-9][a-z0-9-]*$")

# Secret patterns, by the name a refusal prints. The matched text is never printed.
SECRETS = [
    ("sk-ant-", re.compile(r"sk-ant-")),
    ("ghp_", re.compile(r"ghp_")),
    ("gho_", re.compile(r"gho_")),
    ("github_pat_", re.compile(r"github_pat_")),
    ("AKIA access key id", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("private key block", re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")),
    ("Authorization: Bearer token", re.compile(r"Authorization:[ \t]*Bearer[ \t]+[A-Za-z0-9._~+/=-]{8,}")),
]

_TAIL = r"[^\s\"'`<>()\[\]{}|,;*]"
_UNIX = (r"(?:/root|/home/[^/\s\"'`<>]+|/Users/[^/\s\"'`<>]+|/tmp|/var/folders)"
         r"(?=[/\s\"'`<>()\[\]{}|,;:.!?]|$)(?:/" + _TAIL + r"*)?")
_WIN = r"[A-Za-z]:(?:\\+|/)Users(?:\\+|/)[^\\/\s\"'`<>]+(?:(?:\\+|/)[^\s\"'`<>]*)?"


def path_regex(repo=None):
    """The regex that finds an absolute local path. A path is not matched when a word character, `.`, `~` or
    `-` comes right before it, so `docs/tmp/x` and `a.b/root/x` are relative paths and stay as written."""
    parts = []
    if repo:
        parts.append(re.escape(repo.rstrip("/\\")) + r"(?=[/\\\s\"'`<>()\[\]{}|,;:.!?]|$)(?:[/\\]" + _TAIL + r"*)?")
    parts += [_UNIX, _WIN]
    return re.compile(r"(?<![\w.~-])(?:" + "|".join(parts) + ")")


def scrub_text(text, repo=None):
    """(text with every absolute local path replaced, number of replacements)."""
    base = repo.rstrip("/\\") if repo else None
    count = [0]

    def sub(match):
        token = match.group(0)
        tail = ""
        while token and token[-1] in ".,:;!?":
            tail = token[-1] + tail
            token = token[:-1]
        count[0] += 1
        if base and token.startswith(base) and token[len(base):len(base) + 1] in ("/", "\\"):
            return PLACEHOLDER + token[len(base):] + tail
        return PLACEHOLDER + tail

    return path_regex(repo).sub(sub, text), count[0]


def scrub_json(value, repo=None):
    """(value with every string, and every key, scrubbed and every `tracePath` set to null, replacements)."""
    count = 0
    if isinstance(value, str):
        return scrub_text(value, repo)
    if isinstance(value, list):
        out = []
        for item in value:
            new, n = scrub_json(item, repo)
            out.append(new)
            count += n
        return out, count
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            new_key, n = scrub_text(key, repo)
            count += n
            if new_key in out:
                raise ValueError("two keys become the same after scrubbing")
            if key == "tracePath":
                count += 0 if item is None else 1
                out[new_key] = None
                continue
            new, n = scrub_json(item, repo)
            out[new_key] = new
            count += n
        return out, count
    return value, 0


def dump_json(doc, original):
    """Serialize `doc` in the style of `original`: the same indentation, and a final newline if it had one."""
    match = re.search(r"\n([ \t]+)\S", original)
    if match:
        indent = match.group(1) if "\t" in match.group(1) else len(match.group(1))
        text = json.dumps(doc, indent=indent, ensure_ascii=False)
    elif '": ' in original or ", " in original:
        text = json.dumps(doc, ensure_ascii=False)
    else:
        text = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
    return text + ("\n" if original.endswith("\n") else "")


def git_email():
    """`git config user.email`, or None when it is not set."""
    try:
        out = subprocess.run(["git", "config", "user.email"], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() or None if out.returncode == 0 else None


def secret_hits(text, email=None):
    """Names of the secret patterns `text` matches. Never the matched text."""
    hits = [name for name, rx in SECRETS if rx.search(text)]
    if email and email.lower() in text.lower():
        hits.append("git config user.email")
    return hits


def scan_texts(name, text, doc=None):
    """Every form of a file's content a pattern must be tried on. JSON escaping can hide a match from the
    serialized text (a tab becomes `\\t`, `-` can be `\\u002d`), so a JSON file is also scanned as decoded
    keys and string values. HTML entities can hide one in a report, so it is also scanned entity-decoded."""
    forms = [text]
    if name.endswith(".json"):
        if doc is None:
            doc = json.loads(text)
        forms += list(strings_of(doc))
    elif name.endswith(".html"):
        forms.append(html.unescape(text))
    return forms


def read_text(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def plugin_dirs(repo):
    return sorted(n for n in os.listdir(os.path.join(repo, "plugins"))
                  if PLUGIN_NAME.match(n) and os.path.isdir(os.path.join(repo, "plugins", n)))


# --- sources -----------------------------------------------------------------------------------------------

RESULT_PATH = re.compile(r"(?:^|[/\\])plugins[/\\]([^/\\]+)[/\\]evals[/\\]results[/\\]([^/\\]+)[/\\]?")


def find_runs(source):
    """[(folder holding aggregate-result.json)] for a source, or [] when it holds none."""
    source = os.path.abspath(source)
    if os.path.isfile(source):
        return [os.path.dirname(source)] if os.path.basename(source) == "aggregate-result.json" else []
    if os.path.isfile(os.path.join(source, "aggregate-result.json")):
        return [source]
    found = glob.glob(os.path.join(source, "*", "aggregate-result.json"))
    found += glob.glob(os.path.join(source, "plugins", "*", "evals", "results", "*", "aggregate-result.json"))
    return sorted(os.path.dirname(p) for p in found)


def plugin_for(folder, doc):
    """The plugin a run belongs to: from its plugins/<p>/evals/results/ path, else suite.plugins[0].name."""
    found = RESULT_PATH.search(folder.replace(os.sep, "/") + "/")
    if found and found.group(2) == os.path.basename(folder):
        return found.group(1)
    plugins = (doc.get("suite") or {}).get("plugins") or []
    first = plugins[0] if plugins else None
    return first if isinstance(first, str) else (first or {}).get("name")


def prepare(folder, repo, email):
    """Plan one run: ({file: new text}, notes) or (None, [refusal lines]). Nothing is written."""
    stamp = os.path.basename(folder)
    label = stamp
    if not NAME.match(stamp):
        return None, ["refused %s: the folder name is not a plain timestamp" % label]
    json_path = os.path.join(folder, "aggregate-result.json")
    if os.path.getsize(json_path) > MAX_BYTES:
        return None, ["refused %s/aggregate-result.json: over 5 MB" % label]
    original = read_text(json_path)
    try:
        doc = json.loads(original)
    except ValueError as exc:
        return None, ["refused %s/aggregate-result.json: not valid JSON (%s)" % (label, exc.__class__.__name__)]
    if not isinstance(doc, dict) or "cases" not in doc:
        return None, ["refused %s/aggregate-result.json: not a claude plugin eval result" % label]
    plugin = plugin_for(folder, doc)
    if not isinstance(plugin, str) or not plugin:
        return None, ["refused %s: cannot tell which plugin it ran under" % label]
    # A plugin is known when plugins/<name>/ exists. `_template` and names with a separator never qualify.
    if not PLUGIN_NAME.match(plugin) or not os.path.isdir(os.path.join(repo, "plugins", plugin)):
        shown = plugin if re.match(r"^[\w.-]{1,64}$", plugin) else "(not a plain name)"
        return None, ["refused %s: unknown plugin '%s' (no plugins/<name>/ folder for it)" % (label, shown)]
    try:
        scrubbed, replaced = scrub_json(doc, repo)
    except ValueError as exc:
        return None, ["refused %s/aggregate-result.json: %s" % (label, exc)]
    texts = {"aggregate-result.json": dump_json(scrubbed, original)}
    docs = {"aggregate-result.json": scrubbed}
    before = {"aggregate-result.json": scan_texts("aggregate-result.json", original, doc)}
    counts = {"aggregate-result.json": replaced}
    html_path = os.path.join(folder, "report.html")
    if os.path.isfile(html_path):
        if os.path.getsize(html_path) > MAX_BYTES:
            return None, ["refused %s/report.html: over 5 MB" % label]
        raw_html = read_text(html_path)
        before["report.html"] = scan_texts("report.html", raw_html)
        texts["report.html"], counts["report.html"] = scrub_text(raw_html, repo)
    problems = []
    for name, text in texts.items():
        if len(text.encode("utf-8")) > MAX_BYTES:
            problems.append("refused %s/%s: over 5 MB" % (label, name))
        forms = before[name] + scan_texts(name, text, docs.get(name))
        for hit in dict.fromkeys(h for form in forms for h in secret_hits(form, email)):
            problems.append("refused %s/%s: matches secret pattern '%s'" % (label, name, hit))
    if problems:
        return None, problems
    return {"plugin": plugin, "stamp": stamp, "texts": texts, "counts": counts}, []


def archive_dir(repo, plugin, stamp):
    folder = os.path.join(repo, "plugins", plugin, "evals", "archive", stamp)
    root = os.path.realpath(os.path.join(repo, "plugins"))
    if not os.path.realpath(folder).startswith(root + os.sep):
        raise ValueError("the archive folder would be outside plugins/")
    return folder


def archive(sources, repo=REPO, replace=False, email=None, out=print):
    """Archive every run under `sources`. All or nothing: one refusal means nothing is written. Returns the
    exit code."""
    folders = []
    for source in sources:
        runs = find_runs(source)
        if not runs:
            out("error: %s holds no aggregate-result.json" % os.path.basename(os.path.abspath(source)))
            return 2
        folders += runs
    plans, refusals, seen = [], [], {}
    for folder in folders:
        plan, problems = prepare(folder, repo, email)
        if plan is None:
            refusals += problems
            continue
        key = (plan["plugin"], plan["stamp"])
        if key in seen and seen[key] != plan["texts"]:
            refusals.append("refused %s: two sources give plugins/%s/evals/archive/%s with different content"
                            % (plan["stamp"], key[0], key[1]))
            continue
        if key in seen:
            continue
        seen[key] = plan["texts"]
        target = archive_dir(repo, plan["plugin"], plan["stamp"])
        plan["target"] = target
        plan["state"] = "new"
        # The supported file set is reconciled as a whole: a file the source lacks is part of the difference.
        existing = {n: os.path.join(target, n) for n in FILES if os.path.isfile(os.path.join(target, n))}
        plan["stale"] = [n for n in existing if n not in plan["texts"]]
        if existing:
            same = set(existing) == set(plan["texts"]) and all(
                read_text(p) == plan["texts"][n] for n, p in existing.items())
            if same:
                plan["state"] = "same"
            elif replace:
                plan["state"] = "replace"
            else:
                refusals.append("refused %s: plugins/%s/evals/archive/%s already holds different content; "
                                "use --replace to overwrite it" % (plan["stamp"], plan["plugin"], plan["stamp"]))
                continue
        plans.append(plan)
    for line in refusals:
        out(line)
    if refusals:
        out("nothing written: %d refusal(s)" % len(refusals))
        return 1
    written = skipped = 0
    for plan in plans:
        rel = "plugins/%s/evals/archive/%s/" % (plan["plugin"], plan["stamp"])
        if plan["state"] == "same":
            skipped += 1
            out("skipped %s (already archived, same content)" % rel)
            continue
        os.makedirs(plan["target"], exist_ok=True)
        for name, text in plan["texts"].items():
            with open(os.path.join(plan["target"], name), "w", encoding="utf-8", newline="") as fh:
                fh.write(text)
        for name in plan["stale"]:
            os.remove(os.path.join(plan["target"], name))
            out("removed %s%s (the source has no %s)" % (rel, name, name))
        written += 1
        out("%s %s (%s; %d path(s) scrubbed)" % (
            "replaced" if plan["state"] == "replace" else "archived", rel, ", ".join(plan["texts"]),
            sum(plan["counts"].values())))
    out("%d archived, %d skipped" % (written, skipped))
    return 0


# --- --check -----------------------------------------------------------------------------------------------

def strings_of(value):
    """Every string value and key of a parsed JSON document."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from strings_of(item)
    elif isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from strings_of(item)


def check(repo=REPO, email=None, out=print):
    """Verify every archived file. Writes nothing. Returns 1 when any offends, else 0."""
    pattern = path_regex(repo)
    offenders = []
    files = sorted(glob.glob(os.path.join(repo, "plugins", "*", "evals", "archive", "*", "*")))
    for path in files:
        rel = os.path.relpath(path, repo).replace(os.sep, "/")
        if not os.path.isfile(path):
            continue
        if os.path.getsize(path) > MAX_BYTES:
            offenders.append("%s: over 5 MB" % rel)
            continue
        text = read_text(path)
        try:
            forms = scan_texts(path, text)
        except ValueError:
            forms = [text]
            offenders.append("%s: not valid JSON" % rel)
        # Scrubbed text holds `<local>`, so a remaining match is a path that was never scrubbed.
        if any(pattern.search(form) for form in forms):
            offenders.append("%s: absolute local path" % rel)
        for hit in dict.fromkeys(h for form in forms for h in secret_hits(form, email)):
            offenders.append("%s: secret pattern '%s'" % (rel, hit))
    for line in offenders:
        out("offender " + line)
    out("checked %d archived file(s): %s" % (len(files), "%d offender(s)" % len(offenders) if offenders else "clean"))
    return 1 if offenders else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("sources", nargs="*", metavar="SOURCE",
                        help="a results/<timestamp>/ folder, an aggregate-result.json, or a folder holding "
                             "plugins/*/evals/results/*")
    parser.add_argument("--replace", action="store_true",
                        help="overwrite an archived run of the same timestamp whose content differs")
    parser.add_argument("--check", action="store_true",
                        help="verify the archived files (no local path, no secret, none over 5 MB); write nothing")
    args = parser.parse_args(argv)
    email = git_email()
    if args.check:
        if args.sources or args.replace:
            parser.error("--check takes no source and no --replace")
        return check(REPO, email)
    if not args.sources:
        parser.error("give at least one source, or --check")
    return archive(args.sources, REPO, args.replace, email)


if __name__ == "__main__":
    sys.exit(main())
