#!/usr/bin/env python3
"""Write an HTML board of every eval case, grouped by skill, with the results of local runs.

`claude plugin eval` writes one `aggregate-result.json` per run under
`plugins/<plugin>/evals/results/<timestamp>/` (git-ignored, so results stay on the machine
that ran them). Its own `report.html` shows one run of one plugin. This board shows every
skill at once: which cases make it fire, which must keep it quiet, which test its behavior,
and the latest score of each case, with the runs before it.

    python3 tools/build_eval_board.py                      # writes eval-board.html
    python3 tools/build_eval_board.py --out board.html     # another path
    python3 tools/build_eval_board.py --results a.json     # add result files from elsewhere

The page is one self-contained file that makes no network requests. Its interface switches
between English and Vietnamese; case text stays as written in the repository.
Standard library only.
"""

import argparse
import glob
import html
import json
import os
import re
import subprocess
import calendar
import time
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SKILL_IN_MATCH = re.compile(r"\(\?:\[\\w-\]\+:\)\?([a-z0-9-]+)")


def frontmatter(text):
    """The YAML frontmatter of a case or grader file as {key: raw value}, one line per key."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end < 0:
        return {}, text
    fields = {}
    for line in text[3:end].splitlines():
        m = re.match(r"^([A-Za-z_]+):\s*(.*)$", line)
        if m:
            fields[m.group(1)] = m.group(2).strip()
    return fields, text[end + 4:].strip()


def unquote(value):
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def short(text, limit=170):
    """The description's opening, cut at a word boundary: the full text is in the SKILL.md."""
    text = re.split(r" (?:—|-) | \(|\. ", text, maxsplit=1)[0].rstrip(".")
    if len(text) <= limit:
        return text + "."
    return text[:limit].rsplit(" ", 1)[0].rstrip(",;:") + "…"


def last_change(path):
    """Unix time of the last commit that touched `path`, or None outside git or for an untracked path."""
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%ct", "--", path], cwd=REPO,
                             capture_output=True, text=True, timeout=20).stdout.strip()
        return int(out) if out else None
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


STAMP_TIME = re.compile(r"(\d{4}-\d\d-\d\dT\d\d-\d\d-\d\d)")


def stamp_time(stamp, path=None):
    """Unix time of a run, from its results folder name (UTC), else the file's modification time."""
    found = STAMP_TIME.search(stamp or "")
    if found:
        return calendar.timegm(time.strptime(found.group(1), "%Y-%m-%dT%H-%M-%S"))
    try:
        return int(os.path.getmtime(path)) if path else None
    except OSError:
        return None


def plugin_version(plugin_dir):
    return json.loads(read(os.path.join(plugin_dir, ".github", "plugin", "plugin.json"))).get("version")


def skills_of(plugin_dir):
    """[(skill, one-line description, last changed)] in the order the plugin's manifest lists them."""
    manifest = json.loads(read(os.path.join(plugin_dir, ".github", "plugin", "plugin.json")))
    found = []
    for entry in manifest.get("skills", []):
        name = os.path.basename(entry.rstrip("/"))
        fields, _ = frontmatter(read(os.path.join(plugin_dir, entry, "SKILL.md")))
        description = unquote(fields.get("description", ""))
        found.append((name, short(description), last_change(os.path.join(plugin_dir, entry))))
    return found


def grader(path):
    fields, body = frontmatter(read(path))
    g = {"name": os.path.basename(path)[:-3], "type": fields.get("type", "?"), "rubric": body}
    if g["type"] == "tool_used":
        g["tool"] = fields.get("tool", "")
        g["match"] = unquote(fields.get("input_match", ""))
        match = SKILL_IN_MATCH.search(g["match"])
        g["skill"] = match.group(1) if match and g["tool"] == "Skill" else None
        g["min"] = int(fields["min"]) if fields.get("min", "").isdigit() else 1
        g["max"] = int(fields["max"]) if fields.get("max", "").isdigit() else None
    return g


def catalog(repo=REPO):
    """Every plugin with eval cases: its skills and its cases, each case tied to the skills it tests."""
    plugins = []
    for plugin_dir in sorted(glob.glob(os.path.join(repo, "plugins", "*"))):
        plugin = os.path.basename(plugin_dir)
        if plugin.startswith("_") or not os.path.isdir(os.path.join(plugin_dir, "skills")):
            continue
        skills = skills_of(plugin_dir)
        names = [s[0] for s in skills]
        cases = []
        for prompt in sorted(glob.glob(os.path.join(plugin_dir, "evals", "*", "*", "prompt.md"))):
            case_dir = os.path.dirname(prompt)
            fields, body = frontmatter(read(prompt))
            graders = [grader(p) for p in sorted(glob.glob(os.path.join(case_dir, "graders", "*.md")))]
            fires = sorted({g["skill"] for g in graders if g.get("skill") and g["min"] >= 1})
            quiet = sorted({g["skill"] for g in graders if g.get("skill") and g["max"] == 0})
            cases.append({
                "name": os.path.basename(case_dir),
                "kind": os.path.basename(os.path.dirname(case_dir)),
                "description": unquote(fields.get("description", "")),
                "prompt": body,
                "graders": graders,
                "fires": fires,
                # A case that names no skill at all is about the plugin's whole surface.
                "quiet": quiet,
                "skills": sorted(set(fires) | {s for s in quiet if s in names}) or names,
            })
        plugins.append({"name": plugin, "version": plugin_version(plugin_dir), "skills": skills, "cases": cases})
    return plugins


RESULTS_DIR = re.compile(r"plugins[/\\]([^/\\]+)[/\\]evals[/\\]results[/\\]")


def plugin_of(path, doc):
    """The plugin a result file belongs to: from its results/ folder, else from the suite it names.

    Case names repeat across plugins (`none-implement-feature` is in two), so a result whose plugin
    cannot be told is not shown at all rather than shown under the wrong one."""
    found = RESULTS_DIR.search(os.path.abspath(path))
    if found:
        return found.group(1)
    plugins = (doc.get("suite") or {}).get("plugins") or []
    names = [p if isinstance(p, str) else (p or {}).get("name") for p in plugins]
    names = [n for n in names if n]
    return names[0] if len(names) == 1 else None


def load_results(entries):
    """{"<plugin>/<case>": [run, ...] newest first}, from aggregate-result.json documents
    (schemaVersion 1). Each entry is a path, or (plugin, path) when the plugin is given."""
    runs = {}
    for entry in entries:
        plugin, path = entry if isinstance(entry, tuple) else (None, entry)
        try:
            doc = json.loads(read(path))
        except (OSError, ValueError) as exc:
            print("skipped %s: %s" % (path, exc), file=sys.stderr)
            continue
        if not isinstance(doc, dict) or "cases" not in doc:
            print("skipped %s: not a claude plugin eval result" % path, file=sys.stderr)
            continue
        plugin = plugin or plugin_of(path, doc)
        if not plugin:
            print("skipped %s: cannot tell which plugin it is for; pass --results <plugin>=%s"
                  % (path, path), file=sys.stderr)
            continue
        stamp = os.path.basename(os.path.dirname(path)) if path.endswith("aggregate-result.json") \
            else os.path.splitext(os.path.basename(path))[0]
        for case in doc.get("cases") or []:
            agg = case.get("aggregates") or {}
            arms = case.get("arms") or {}
            with_runs = arms.get("with") or []
            errors = sorted({r.get("error") for r in with_runs if isinstance(r, dict) and r.get("error")})
            runs.setdefault("%s/%s" % (plugin, case.get("name")), []).append({
                "stamp": stamp,
                "time": stamp_time(stamp, path),
                # claude plugin eval writes no host; tools/copilot_eval.py writes "copilot".
                "host": doc.get("host") or "claude",
                "model": doc.get("model"),
                "score": agg.get("score"),
                "delta": agg.get("delta"),
                "runs": len(with_runs),
                "errors": errors,
                "partial": bool(doc.get("partial")),
                "partialReason": doc.get("partialReason"),
                "skippedPaid": any(isinstance(r, dict) and r.get("skippedPaidGraders") for r in with_runs),
            })
    for history in runs.values():
        history.sort(key=lambda r: r["stamp"], reverse=True)
    return runs


def trusted(run):
    """A run whose score means something: the suite finished and no run of the case errored."""
    return run["score"] is not None and not run["partial"] and not run["errors"] and not run["skippedPaid"]


def result_files(repo=REPO):
    return sorted(glob.glob(os.path.join(repo, "plugins", "*", "evals", "results", "*", "aggregate-result.json")))


# The hosts an eval can run on and a plugin can be installed in. tools/skill_manager.py builds its
# commands from `exe`, and the page draws its badges, run forms and platform buttons from this list,
# so a new host is one entry here (plus how to read its `plugin list --json` in skill_manager.installed).
HOSTS = [
    {"id": "copilot", "label": "Copilot CLI", "short": "Copilot", "exe": "copilot"},
    {"id": "claude", "label": "Claude Code", "short": "Claude", "exe": "claude"},
]


def board(plugins, results, server=None):
    """The page. `server` is set only when tools/skill_manager.py serves it: {"token": ...}. A static
    file has no server, so it shows no Run controls."""
    data = {"plugins": plugins, "results": results, "hosts": HOSTS}
    payload = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
    return PAGE.replace("__DATA__", payload).replace("__SERVER__", json.dumps(server))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--out", default=os.path.join(REPO, "eval-board.html"))
    parser.add_argument("--results", nargs="*", default=[], metavar="[PLUGIN=]FILE",
                        help="extra aggregate-result.json or --json files; prefix the plugin when the "
                             "file is not under plugins/<plugin>/evals/results/")
    args = parser.parse_args(argv)
    plugins = catalog()
    files = result_files() + [tuple(r.split("=", 1)) if re.match(r"^[a-z0-9-]+=", r) else r for r in args.results]
    results = load_results(files)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(board(plugins, results))
    cases = sum(len(p["cases"]) for p in plugins)
    scored = sum(1 for history in results.values() if any(trusted(r) for r in history))
    print("wrote %s: %d cases, %d result file(s), %d case(s) with a trusted score"
          % (args.out, cases, len(files), scored))
    return 0


PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Skills Eval Board</title>
<style>
/* Two views a person switches between (Evals, Install) and one the page opens for a job (Run). */
:root{
  --bg:#f4f6fb; --panel:#fff; --ink:#151a2d; --muted:#5b6380; --line:#dde2ee;
  --accent:#2f4bd8; --accent-soft:#e6eafd;
  --ok:#1f7a4d; --ok-soft:#e1f3ea; --warn:#9a5b00; --warn-soft:#fbefd9; --bad:#b3261e; --bad-soft:#fbe3e1;
  --trig:#6b3fc4; --trig-soft:#efe8fb; --beh:#0b7285; --beh-soft:#dff2f5;
  --sans:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  --mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; color-scheme:light;
}
@media (prefers-color-scheme: dark){:root{
  --bg:#0f1220; --panel:#171b2e; --ink:#e7eaf6; --muted:#9aa3c2; --line:#2a3050;
  --accent:#8fa2ff; --accent-soft:#232b55;
  --ok:#5fd39a; --ok-soft:#123425; --warn:#f0b656; --warn-soft:#3a2a10; --bad:#ff8a80; --bad-soft:#3d1716;
  --trig:#b89bff; --trig-soft:#2a2148; --beh:#5fd0e0; --beh-soft:#10313a; color-scheme:dark}}
*{box-sizing:border-box}
[hidden]{display:none!important}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 var(--sans)}
.wrap{max-width:1320px;margin:0 auto;padding:16px 16px 64px;display:flex;flex-direction:column;gap:18px}
h1,h2,h3{margin:0;line-height:1.25;text-wrap:balance} h1{font-size:1.35rem} h2{font-size:1.15rem} h3{font-size:1rem}
p{margin:0;max-width:72ch}
a{color:var(--accent)}
.mono,code{font-family:var(--mono);font-size:.86em}
.eyebrow{font-family:var(--mono);font-size:.72rem;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
.muted{color:var(--muted)} .foot{color:var(--muted);font-size:.82rem}
button:focus-visible,input:focus-visible,select:focus-visible,a:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
[data-view]{display:flex;flex-direction:column;gap:16px}

/* Header: name, the two tabs, host status, the running job, language. */
header.top{display:flex;flex-wrap:wrap;gap:10px 18px;align-items:center;border-bottom:1px solid var(--line);padding-bottom:10px}
.brand{display:flex;flex-direction:column;gap:0;margin-right:auto}
.tabs{display:flex;gap:2px}
.tabs button{font:inherit;font-size:.92rem;border:0;border-bottom:2px solid transparent;background:transparent;color:var(--muted);padding:8px 14px;cursor:pointer;min-height:40px}
.tabs button[aria-selected="true"]{color:var(--ink);border-bottom-color:var(--accent);font-weight:600}
.hoststatus{display:flex;gap:6px;flex-wrap:wrap}
.lang{display:flex;border:1px solid var(--line);border-radius:999px;overflow:hidden;background:var(--panel)}
.lang button{font:inherit;font-size:.82rem;border:0;background:transparent;color:var(--ink);padding:5px 12px;cursor:pointer}
.lang button[aria-pressed="true"]{background:var(--accent);color:var(--panel)}
#jobchip{cursor:pointer;font:inherit;font-family:var(--mono);font-size:.76rem}

.pill{display:inline-flex;gap:5px;align-items:center;font-family:var(--mono);font-size:.72rem;padding:2px 8px;border-radius:999px;white-space:nowrap;border:1px solid transparent}
.pill.ok{background:var(--ok-soft);color:var(--ok)} .pill.warn{background:var(--warn-soft);color:var(--warn)}
.pill.bad{background:var(--bad-soft);color:var(--bad)} .pill.idle{color:var(--muted);border-color:var(--line)}
.pill.missing{color:var(--muted);border:1px dashed var(--muted)}
.pill.trig{background:var(--trig-soft);color:var(--trig)} .pill.beh{background:var(--beh-soft);color:var(--beh)}
.pill .host{font-weight:600}
.dot{display:inline-block;width:8px;height:8px;border-radius:50%;flex:none}
.dot.ok{background:var(--ok)} .dot.warn{background:var(--warn)} .dot.off{background:transparent;border:1px solid var(--muted)}

.stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}
@media (max-width:760px){.stats{grid-template-columns:repeat(2,minmax(0,1fr))}}
.stat{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:10px 14px;display:flex;flex-direction:column}
.stat b{font-size:1.5rem;font-variant-numeric:tabular-nums} .stat span{color:var(--muted);font-size:.82rem}
.stat.alert{border-color:var(--warn);background:var(--warn-soft)} .stat.alert b{color:var(--warn)}

.toolbar{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
input[type=search]{font:inherit;font-size:.9rem;padding:7px 12px;border-radius:8px;border:1px solid var(--line);background:var(--panel);color:var(--ink);flex:1 1 260px;min-width:0}
.chip{font:inherit;font-size:.84rem;padding:5px 12px;border-radius:999px;border:1px solid var(--line);background:var(--panel);color:var(--ink);cursor:pointer}
.chip[aria-pressed="true"]{background:var(--accent);border-color:var(--accent);color:var(--panel)}
.chip .n{font-family:var(--mono);font-size:.76rem;opacity:.8;margin-left:4px}

/* Evals: the skill list on the left, the chosen case on the right. */
.evals{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,440px);gap:16px;align-items:start}
@media (max-width:1060px){.evals{grid-template-columns:minmax(0,1fr)}}
.skilllist{display:flex;flex-direction:column;border:1px solid var(--line);border-radius:10px;background:var(--panel);overflow:hidden}
.skill{border-top:1px solid var(--line)} .skill:first-child{border-top:0}
.skillhead{display:grid;grid-template-columns:minmax(0,13rem) minmax(0,1fr) auto minmax(0,10rem);gap:6px 14px;padding:12px 14px;cursor:pointer;align-items:start}
.skillhead:hover{background:var(--bg)}
.skill.open>.skillhead{background:var(--accent-soft)}
@media (max-width:760px){.skillhead{grid-template-columns:minmax(0,1fr) auto}.skillhead .goal{grid-column:1/-1;order:3}.skillhead .status{order:2}.skillhead .meta{order:4}}
.skillhead .sub{display:block;color:var(--muted);font-size:.78rem;font-family:var(--mono)}
.skillhead .goal{font-size:.86rem;color:var(--muted)}
.skillhead .meta{grid-column:1/-1;display:flex;gap:6px;flex-wrap:wrap}
.expander{font:inherit;border:0;background:transparent;color:var(--ink);padding:0;cursor:pointer;display:flex;gap:6px;align-items:baseline;text-align:left}
.expander::before{content:"\25B8";color:var(--muted);font-size:.8rem}
.expander[aria-expanded="true"]::before{content:"\25BE"}
.cov3{display:flex;gap:4px}
.cov3 span{font-family:var(--mono);font-size:.74rem;padding:2px 6px;border-radius:6px;background:var(--bg)}
.cov3 span.zero{color:var(--bad);outline:1px dashed var(--bad)}
.stack{display:flex;flex-direction:column;gap:4px;align-items:flex-start}
.skillbody{padding:10px 14px 16px;background:var(--bg);display:flex;flex-direction:column;gap:12px;border-top:1px solid var(--line)}
.runbar{display:flex;flex-direction:column;gap:8px;background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:8px 12px}
.runbar .row{display:flex;flex-wrap:wrap;gap:8px;align-items:center;justify-content:space-between}
.group{display:flex;flex-direction:column;gap:6px}
.caselist{display:flex;flex-direction:column;border:1px solid var(--line);border-radius:8px;background:var(--panel);overflow:hidden}
.caserow{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:2px 10px;width:100%;text-align:left;font:inherit;color:inherit;background:transparent;border:0;border-top:1px solid var(--line);padding:8px 12px;cursor:pointer}
.caserow:first-child{border-top:0} .caserow:hover{background:var(--bg)}
.caserow[aria-current="true"]{background:var(--accent-soft);box-shadow:inset 3px 0 var(--accent)}
.cn{font-family:var(--mono);font-size:.84rem;font-weight:600;overflow-wrap:anywhere}
.cd{grid-column:1/-1;color:var(--muted);font-size:.82rem}
.tags{display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end}
.empty{padding:18px 16px;color:var(--muted)}
.casepanel{position:sticky;top:12px;background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px 16px;display:flex;flex-direction:column;gap:12px;max-height:calc(100vh - 24px);overflow:auto}
@media (max-width:1060px){.casepanel{position:static;max-height:none}}
.casepanel .hd{display:flex;justify-content:space-between;gap:8px;align-items:flex-start}
.prompt{font-family:var(--mono);font-size:.78rem;background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:10px 12px;white-space:pre-wrap;overflow-wrap:anywhere;max-height:260px;overflow:auto}
table{border-collapse:collapse;width:100%;font-size:.8rem} th,td{text-align:left;padding:5px 8px;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--muted);font-weight:500} td.num{font-family:var(--mono);font-variant-numeric:tabular-nums}
.tw{overflow-x:auto}
.gtag{font-family:var(--mono);font-size:.68rem;padding:1px 6px;border-radius:5px;background:var(--bg);border:1px solid var(--line)}
.gtag.tool{color:var(--trig)} .gtag.llm{color:var(--beh)} .gtag.regex{color:var(--warn)}

.runform{display:flex;flex-wrap:wrap;gap:8px;align-items:flex-end}
.runform label{display:flex;flex-direction:column;gap:3px;font-size:.76rem;color:var(--muted)}
.runform select,.runform input{font:inherit;font-size:.85rem;padding:5px 8px;border-radius:8px;border:1px solid var(--line);background:var(--panel);color:var(--ink);min-width:0}
.runform input[type=text]{width:11rem;max-width:100%}
.btn{font:inherit;font-size:.85rem;padding:7px 14px;border-radius:8px;border:1px solid var(--accent);background:var(--accent);color:var(--panel);cursor:pointer;min-height:36px}
.btn.ghost{background:var(--panel);color:var(--accent)}
.btn.small{font-size:.78rem;padding:4px 10px;min-height:30px}
.btn.danger{border-color:var(--bad);background:var(--panel);color:var(--bad)}
.btn:disabled{opacity:.5;cursor:not-allowed}
.confirm{flex-basis:100%;display:flex;flex-wrap:wrap;gap:8px;align-items:center;font-size:.85rem;background:var(--warn-soft);color:var(--ink);padding:8px 10px;border-radius:8px}
.notice{display:flex;flex-wrap:wrap;gap:8px;align-items:center;font-size:.85rem;background:var(--accent-soft);padding:8px 12px;border-radius:8px}
.cmd{font-family:var(--mono);font-size:.8rem;background:var(--bg);padding:2px 6px;border-radius:6px;overflow-wrap:anywhere;white-space:pre-wrap}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px;display:flex;flex-direction:column;gap:10px}
.actions{display:flex;gap:6px;flex-wrap:wrap}

/* Run: the waiting question and its answers on the left, the live output on the right. */
.runhead{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center}
.runhead h2{margin-right:4px}
.runhead .spacer{flex:1}
.back{font:inherit;border:0;background:transparent;color:var(--accent);cursor:pointer;padding:0;align-self:flex-start}
.progress{height:6px;background:var(--line);border-radius:999px;overflow:hidden}
.progress>span{display:block;height:100%;background:var(--accent);transition:width .3s}
.rungrid{display:grid;grid-template-columns:minmax(0,380px) minmax(0,1fr);gap:16px;align-items:start}
@media (max-width:900px){.rungrid{grid-template-columns:minmax(0,1fr)}}
.question{font-weight:600;font-size:1rem}
.answers{display:flex;gap:8px;flex-wrap:wrap}
.ans{font:inherit;font-size:.9rem;padding:8px 16px;border-radius:8px;border:1px solid var(--line);cursor:pointer;display:inline-flex;gap:8px;align-items:center;min-height:42px;background:var(--panel);color:var(--ink)}
.ans .ico{font-weight:700}
.ans.y{background:var(--ok-soft);color:var(--ok);border-color:var(--ok)}
.ans.n{background:var(--bad-soft);color:var(--bad);border-color:var(--bad)}
.ans:disabled{opacity:.5;cursor:not-allowed}
.tally{display:flex;gap:14px;font-family:var(--mono);font-size:.85rem}
.tally b{font-size:1.2rem}
.log{margin:0;min-height:340px;max-height:72vh;overflow:auto;font-family:var(--mono);font-size:.76rem;line-height:1.5;background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:10px 12px;white-space:pre-wrap;overflow-wrap:anywhere}
.log span{display:block}
.log .l-cmd{color:var(--accent);font-weight:600}
.log .l-sec{font-weight:700;margin-top:8px}
.log .l-grader{color:var(--trig)}
.log .l-pass{color:var(--ok)} .log .l-fail,.log .l-err{color:var(--bad)}
.log .l-q{color:var(--warn);font-weight:600} .log .l-ans{color:var(--muted)}
.log .l-score{font-weight:700}

/* Install: one platform at a time. */
.platforms{display:flex;gap:8px;flex-wrap:wrap}
.platform{font:inherit;display:flex;flex-direction:column;align-items:flex-start;gap:2px;padding:10px 14px;border-radius:10px;border:1px solid var(--line);background:var(--panel);color:var(--ink);cursor:pointer;min-width:200px;text-align:left}
.platform b{display:flex;gap:8px;align-items:center}
.platform span{font-size:.8rem;color:var(--muted)}
.platform[aria-pressed="true"]{border-color:var(--accent);box-shadow:inset 0 0 0 1px var(--accent)}
.grid{background:var(--panel);border:1px solid var(--line);border-radius:10px;overflow-x:auto}
.grid table{min-width:720px} .grid td,.grid th{padding:10px 12px;vertical-align:middle}
.grid td .sub{display:block;color:var(--muted);font-size:.76rem}
.slots{display:grid;grid-template-columns:repeat(2,7.5rem);gap:6px}
.slots .btn{width:100%}
.slots .hold{visibility:hidden}
</style>
</head>
<body>
<div class="wrap">
<header class="top">
  <div class="brand"><span class="eyebrow">eurus-labs/Skills</span><h1 id="title"></h1></div>
  <nav class="tabs" role="tablist" aria-label="Views">
    <button type="button" role="tab" data-tab="evals" id="tab-evals"></button>
    <button type="button" role="tab" data-tab="install" id="tab-install" hidden></button>
  </nav>
  <div class="hoststatus" id="hoststatus"></div>
  <button type="button" class="pill warn" id="jobchip" hidden></button>
  <div class="lang" role="group" aria-label="Language">
    <button type="button" data-lang="en">English</button><button type="button" data-lang="vi">Tiếng Việt</button>
  </div>
</header>

<div data-view="evals">
  <p class="muted" data-i18n="lede"></p>
  <section><div class="stats" id="stats"></div><p class="foot" id="trustnote"></p></section>
  <div class="toolbar"><input type="search" id="q"><div class="toolbar" id="filters"></div></div>
  <div class="evals"><div class="skilllist" id="skilllist"></div><aside class="casepanel" id="casepanel" aria-live="polite"></aside></div>
  <p class="foot" data-i18n="foot"></p>
  <p class="foot" id="runhint"></p>
</div>

<div data-view="install" hidden>
  <section><h2 data-i18n="installTitle"></h2><p class="muted" data-i18n="installLede"></p></section>
  <div class="platforms" id="platforms"></div>
  <div id="installconfirm"></div>
  <div id="installbody" style="display:flex;flex-direction:column;gap:12px"></div>
</div>

<div data-view="run" hidden>
  <button type="button" class="back" id="runback"></button>
  <div class="runhead" id="runhead"></div>
  <div class="progress"><span id="runbar" style="width:0"></span></div>
  <div class="rungrid"><div style="display:flex;flex-direction:column;gap:12px" id="runside"></div>
    <div style="display:flex;flex-direction:column;gap:6px"><span class="eyebrow" id="outputlabel"></span><pre class="log" id="runlog"></pre></div></div>
</div>
</div>
<script>
let DATA = __DATA__;
const SERVER = __SERVER__;
const T = {
 en:{title:"Skills eval board", titleManager:"Skill manager",
  lede:"Every skill with its eval cases and the latest local run of each on every host, kept apart. A case's score is its with-plugin score; Δ is how far that is above the run without the plugin. Click a skill to open its cases.",
  cases:"eval cases", skillsCovered:"skills with a case", trusted:"cases with a trusted score", files:"result files read",
  trustnote:"A score counts as trusted only when the suite finished and no run of the case ended in an error. Partial suites (cost ceiling, interrupted, failed sign-in) are shown but never trusted.",
  fires:"fires", quiet:"quiet", behavior:"behavior", noCases:"No eval cases yet.",
  gFires:"Must fire: the skill must be called", gQuiet:"Must stay quiet: the skill must not be called", gBehavior:"Behavior: grades what the skill does",
  search:"Search skills and cases…", fAll:"All", fNotRun:"Not run", fNoEvals:"No evals", noMatch:"No skill matches the search and filter.",
  pickCase:"Pick a case to see its prompt, graders, runs and Run form.", closePanel:"Close",
  runAllOf:"Run all {n} cases of {skill}", casesN:"{n} cases",
  notRun:"not run", untrusted:"untrusted", runs:"runs",
  prompt:"Prompt sent to the agent", graders:"Graders", history:"Runs", when:"Run", score:"Score", note:"Note",
  partial:"partial", error:"error", skippedPaid:"judge graders skipped",
  indicator:"plugin-fired indicator, not scored", mustNot:"must not call", must:"must call",
  matching:"with input matching", lastTrusted:"last trusted", host:"Host",
  foot:"Generated by tools/build_eval_board.py from plugins/*/evals and the git-ignored plugins/*/evals/results/. Re-run it after each eval run.",
  runHint:"To run a case from this page, start it with: python3 tools/skill_manager.py",
  runCase:"Run this case", runHost:"Host", runArms:"Arms", armsBoth:"with and without the plugin", armsWith:"with the plugin only",
  runModel:"Model (blank = default)", runEffort:"Reasoning effort (Copilot)", effortDefault:"default", runCost:"Cost ceiling, USD (Claude)",
  start:"Run…", confirmRun:"Runs {case} on {host}, {arms}. It is billed to your plan and may take minutes.", confirm:"Start", cancel:"Cancel",
  stop:"Stop", sRunning:"running", sWaiting:"waiting for you", sDone:"finished", sFailed:"failed", sStopped:"stopped", sStopping:"stopping",
  yes:"Yes", no:"No", skip:"Skip", stopHint:"Stop takes effect at the next question or when the current command ends.",
  qHint:"Answer from the transcript: what did the agent actually do?",
  backEvals:"← Back to evals", backInstall:"← Back to install", caseOf:"case {i} of {n}", stepOf:"step {i} of {n}", costCeil:"cost ceiling ${c}",
  working:"Working. A question appears here when the run needs your judgement.",
  mDone:"Finished. The scores are on the Evals tab.", mStopped:"Stopped. What was graded so far is saved.", mFailed:"Failed. The output says why.",
  mStopping:"Stopping. It takes effect at the next question or when the current command ends.",
  transcripts:"Transcripts", noTranscripts:"No transcript yet.", tally:"Answers so far", output:"Output", jobChip:"● {s}: {t}",
  tabInstall:"Install", tabEvals:"Evals",
  colInstalled:"Installed", colLatest:"Latest runs",
  stNoEvals:"no evals", stNotRun:"not run", stUntrusted:"no trusted run", stPartly:"partly run ({k}/{n})", stNeedsWork:"needs work", stPassing:"passing", stChanged:"changed since last run", stLatestUntrusted:"latest run untrusted ({k})", untrustedN:"{k} untrusted",
  runAll:"Run all cases…", passOf:"{p}/{n} pass", loading:"Loading…", notFound:"not found on PATH", notInstalled:"not installed",
  installTitle:"Install plugins", installLede:"Choose a platform, then install, update or remove this marketplace's plugins in it. Every action shows its command and runs only after you confirm.",
  marketplace:"Marketplace", notRegistered:"not registered", registerFirst:"Register the marketplace first: the plugin actions need it.",
  fromCheckout:"Register from this checkout", fromGithub:"Register from GitHub", updateMarket:"Update marketplace",
  colPlugin:"Plugin", colHere:"In this checkout", colIn:"In {host}", install:"Install", update:"Update", uninstall:"Uninstall", installAll:"Install all", updateAll:"Update all",
  willRun:"This runs:", older:"older", refresh:"Refresh", disabled:"disabled", nInstalled:"{k} of {n} installed",
  fixPath:"{label} was not found on PATH. Install it, open a new terminal so that `{exe}` runs, start this manager again from there, then Refresh.",
  installRunning:"Running: {t}", showOutput:"Show output"},
 vi:{title:"Bảng eval của các skill", titleManager:"Quản lý skill",
  lede:"Mọi skill cùng các case eval của nó và lần chạy local mới nhất của từng case trên mỗi host, tách riêng từng host. Điểm của case là điểm khi có plugin; Δ là chênh lệch so với lượt chạy không có plugin. Bấm vào một skill để mở các case của nó.",
  cases:"case eval", skillsCovered:"skill có case", trusted:"case có điểm tin được", files:"file kết quả đã đọc",
  trustnote:"Điểm chỉ được tin khi cả suite chạy xong và không lượt nào của case bị lỗi. Suite dở dang (chạm trần chi phí, bị ngắt, đăng nhập lỗi) vẫn hiện nhưng không bao giờ được tin.",
  fires:"phải gọi", quiet:"phải im", behavior:"hành vi", noCases:"Chưa có case eval nào.",
  gFires:"Phải gọi: skill phải được gọi", gQuiet:"Phải im: skill không được gọi", gBehavior:"Hành vi: chấm việc skill làm",
  search:"Tìm skill và case…", fAll:"Tất cả", fNotRun:"Chưa chạy", fNoEvals:"Chưa có eval", noMatch:"Không có skill nào khớp ô tìm kiếm và bộ lọc.",
  pickCase:"Chọn một case để xem prompt, grader, các lần chạy và form chạy.", closePanel:"Đóng",
  runAllOf:"Chạy cả {n} case của {skill}", casesN:"{n} case",
  notRun:"chưa chạy", untrusted:"không tin được", runs:"lượt",
  prompt:"Câu hỏi gửi agent", graders:"Grader", history:"Các lần chạy", when:"Lần chạy", score:"Điểm", note:"Ghi chú",
  partial:"dở dang", error:"lỗi", skippedPaid:"bỏ qua grader dùng model",
  indicator:"chỉ báo plugin được gọi, không tính điểm", mustNot:"không được gọi", must:"phải gọi",
  matching:"với input khớp", lastTrusted:"tin được gần nhất", host:"Host",
  foot:"Sinh bởi tools/build_eval_board.py từ plugins/*/evals và thư mục plugins/*/evals/results/ (bị git bỏ qua). Chạy lại sau mỗi lần chạy eval.",
  runHint:"Để chạy case ngay trên trang này, mở nó bằng: python3 tools/skill_manager.py",
  runCase:"Chạy case này", runHost:"Host", runArms:"Lượt", armsBoth:"có và không có plugin", armsWith:"chỉ có plugin",
  runModel:"Model (để trống = mặc định)", runEffort:"Reasoning effort (Copilot)", effortDefault:"mặc định", runCost:"Trần chi phí, USD (Claude)",
  start:"Chạy…", confirmRun:"Chạy {case} trên {host}, {arms}. Lần chạy tính phí vào gói của bạn và có thể mất vài phút.", confirm:"Bắt đầu", cancel:"Huỷ",
  stop:"Dừng", sRunning:"đang chạy", sWaiting:"chờ bạn trả lời", sDone:"xong", sFailed:"lỗi", sStopped:"đã dừng", sStopping:"đang dừng",
  yes:"Có", no:"Không", skip:"Bỏ qua", stopHint:"Dừng có hiệu lực ở câu hỏi tiếp theo hoặc khi lệnh hiện tại kết thúc.",
  qHint:"Trả lời theo transcript: agent đã thực sự làm gì?",
  backEvals:"← Về Evals", backInstall:"← Về Cài đặt", caseOf:"case {i}/{n}", stepOf:"bước {i}/{n}", costCeil:"trần chi phí ${c}",
  working:"Đang chạy. Câu hỏi sẽ hiện ở đây khi lượt chạy cần bạn đánh giá.",
  mDone:"Xong. Điểm ở tab Evals.", mStopped:"Đã dừng. Phần đã chấm vẫn được lưu.", mFailed:"Lỗi. Xem output để biết lý do.",
  mStopping:"Đang dừng. Có hiệu lực ở câu hỏi tiếp theo hoặc khi lệnh hiện tại kết thúc.",
  transcripts:"Transcript", noTranscripts:"Chưa có transcript.", tally:"Đã trả lời", output:"Output", jobChip:"● {s}: {t}",
  tabInstall:"Cài đặt", tabEvals:"Evals",
  colInstalled:"Đã cài", colLatest:"Lần chạy gần nhất",
  stNoEvals:"chưa có eval", stNotRun:"chưa chạy", stUntrusted:"chưa có lần chạy tin được", stPartly:"chạy một phần ({k}/{n})", stNeedsWork:"cần sửa", stPassing:"đạt", stChanged:"đã đổi từ lần chạy cuối", stLatestUntrusted:"lần chạy mới nhất không tin được ({k})", untrustedN:"{k} không tin được",
  runAll:"Chạy mọi case…", passOf:"{p}/{n} đạt", loading:"Đang tải…", notFound:"không có trong PATH", notInstalled:"chưa cài",
  installTitle:"Cài plugin", installLede:"Chọn một nền tảng, rồi cài, cập nhật hoặc gỡ các plugin của marketplace này trên đó. Mỗi thao tác hiện lệnh sẽ chạy và chỉ chạy sau khi bạn xác nhận.",
  marketplace:"Marketplace", notRegistered:"chưa đăng ký", registerFirst:"Hãy đăng ký marketplace trước: các thao tác với plugin cần nó.",
  fromCheckout:"Đăng ký từ bản checkout này", fromGithub:"Đăng ký từ GitHub", updateMarket:"Cập nhật marketplace",
  colPlugin:"Plugin", colHere:"Trong checkout này", colIn:"Trong {host}", install:"Cài", update:"Cập nhật", uninstall:"Gỡ", installAll:"Cài tất cả", updateAll:"Cập nhật tất cả",
  willRun:"Sẽ chạy:", older:"cũ hơn", refresh:"Tải lại", disabled:"đang tắt", nInstalled:"đã cài {k}/{n}",
  fixPath:"Không tìm thấy {label} trong PATH. Hãy cài nó, mở terminal mới để lệnh `{exe}` chạy được, khởi động lại trình quản lý này từ terminal đó, rồi bấm Tải lại.",
  installRunning:"Đang chạy: {t}", showOutput:"Xem output"}
};
let lang = "en";
try { const saved = localStorage.getItem("eval-board-lang"); if (saved === "vi" || saved === "en") lang = saved; } catch (e) {}
/* view: what is shown; back: where the Run view returns to; expanded: skills whose cases are shown;
   skillForm: the skill whose run-all form is open; selected: the case in the panel. */
const state = {view:"evals", back:"evals", q:"", filter:"all", expanded:new Set(), skillForm:null, selected:null,
  form:{}, confirming:null, installing:null, platform:null};
let INSTALLED = null;
const t = k => T[lang][k];
const fill = (s, o) => Object.keys(o).reduce((a, k) => a.split("{" + k + "}").join(o[k]), s);
const esc = s => String(s == null ? "" : s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const $ = id => document.getElementById(id);
let ALL = [], HOSTS = [];
function setData(d){ DATA = d; HOSTS = DATA.hosts || []; ALL = DATA.plugins.flatMap(p => p.cases.map(c => Object.assign({plugin:p.name}, c))); }
setData(DATA);
const trusted = r => r.score != null && !r.partial && !r.errors.length && !r.skippedPaid;
const keyOf = c => c.plugin + "/" + c.name;
const f2 = v => v == null ? "—" : (+v).toFixed(2);
const hostOf = id => HOSTS.find(h => h.id === id) || {id, label: id, short: id, exe: id};
const hostName = id => hostOf(id).short;

function scored(r){
  const cls = r.score >= 0.8 ? "ok" : r.score >= 0.5 ? "warn" : "bad";
  const d = r.delta == null ? "" : ` · Δ ${r.delta >= 0 ? "+" : ""}${(+r.delta).toFixed(2)}`;
  return [cls, `${f2(r.score)}${d}`];
}
/* One badge per host, never mixed: a skill can trigger on Claude and stay silent on Copilot.
   Each badge is that host's newest run. When it cannot be trusted, the host's last trusted score
   follows it, labelled as such, so an old pass never stands in for a newer failure. */
function hostPill(host, h){
  const r = h[0], label = `<b class="host">${esc(hostName(host))}</b>`;
  if (trusted(r)) { const [cls, txt] = scored(r); return `<span class="pill ${cls}">${label}${txt}</span>`; }
  const warn = `<span class="pill warn" title="${esc(r.errors.join("; ") || r.partialReason || "")}">${label}${t("untrusted")}</span>`;
  const prev = h.find(trusted);
  if (!prev) return warn;
  const [, txt] = scored(prev);
  return warn + `<span class="pill idle" title="${esc(prev.stamp)}">${t("lastTrusted")} ${txt}</span>`;
}
function scorePill(key){
  const all = DATA.results[key] || [];
  if (!all.length) return `<span class="pill idle">${t("notRun")}</span>`;
  const hosts = [...HOSTS.map(h => h.id), ...new Set(all.map(r => r.host))].filter((v, i, a) => a.indexOf(v) === i);
  return hosts.map(host => { const h = all.filter(r => r.host === host); return h.length ? hostPill(host, h) : ""; }).join("");
}

function stats(){
  const skills = DATA.plugins.flatMap(p => p.skills.map(s => s[0]));
  const covered = new Set(ALL.flatMap(c => c.skills));
  const scoredN = ALL.filter(c => (DATA.results[keyOf(c)] || []).some(trusted)).length;
  const files = new Set(Object.values(DATA.results).flat().map(r => r.stamp)).size;
  $("stats").innerHTML =
    `<div class="stat"><b>${ALL.length}</b><span>${t("cases")}</span></div>`+
    `<div class="stat"><b>${skills.filter(s => covered.has(s)).length} / ${skills.length}</b><span>${t("skillsCovered")}</span></div>`+
    `<div class="stat ${scoredN ? "" : "alert"}"><b>${scoredN}</b><span>${t("trusted")}</span></div>`+
    `<div class="stat"><b>${files}</b><span>${t("files")}</span></div>`;
  $("trustnote").textContent = t("trustnote");
}

/* A skill's cases, split by what they ask of it. A case that names two skills (a fire case with a quiet
   grader for its sibling) is listed under each, in the direction it tests that skill. */
function casesOf(p, skill){
  const mine = p.cases.filter(c => c.skills.includes(skill)).map(c => Object.assign({plugin:p.name}, c));
  return {all: mine,
    fires: mine.filter(c => c.kind === "trigger" && c.fires.includes(skill)),
    quiet: mine.filter(c => c.kind === "trigger" && !c.fires.includes(skill)),
    behavior: mine.filter(c => c.kind === "behavior")};
}
function skillStatus(p, skill, changed){
  const mine = p.cases.filter(c => c.skills.includes(skill));
  if (!mine.length) return {kind:"noevals", chips:[["bad", t("stNoEvals")]], hosts:{}};
  const hosts = {};
  let anyRun = false, newest = 0;
  const trustedCases = new Set(), failing = new Set(), untrustedLatest = new Set();
  for (const c of mine) {
    const runs = DATA.results[p.name + "/" + c.name] || [];
    if (runs.length) anyRun = true;
    for (const r of runs) newest = Math.max(newest, r.time || 0);
    for (const host of new Set(runs.map(r => r.host))) {
      /* The newest run decides: an older pass never stands in for a newer untrusted run. */
      const latest = runs.filter(r => r.host === host)[0];
      const slot = hosts[host] = hosts[host] || {pass:0, n:0, untrusted:0};
      if (!trusted(latest)) { slot.untrusted++; untrustedLatest.add(c.name); continue; }
      slot.n++; trustedCases.add(c.name);
      if (latest.score >= 0.8) slot.pass++; else failing.add(c.name);
    }
  }
  const chips = [];
  if (!anyRun) chips.push(["idle", t("stNotRun")]);
  else if (failing.size) chips.push(["bad", t("stNeedsWork")]);
  else if (!trustedCases.size) chips.push(["warn", t("stUntrusted")]);
  else if (untrustedLatest.size) chips.push(["warn", t("stLatestUntrusted").replace("{k}", untrustedLatest.size)]);
  else if (trustedCases.size < mine.length) chips.push(["warn", t("stPartly").replace("{k}", trustedCases.size).replace("{n}", mine.length)]);
  else chips.push(["ok", t("stPassing")]);
  if (anyRun && changed && newest && changed > newest) chips.push(["warn", t("stChanged")]);
  return {kind: anyRun ? "run" : "notrun", chips, hosts};
}
function installedChips(plugin, version){
  if (!SERVER) return "";
  if (!INSTALLED) return `<span class="pill idle">${t("loading")}</span>`;
  return HOSTS.map(host => {
    const h = INSTALLED[host.id]; if (!h || !h.available) return "";
    const got = h.plugins[plugin];
    if (!got) return `<span class="pill missing">${esc(host.short)} · ${t("notInstalled")}</span>`;
    return `<span class="pill ${!got.enabled ? "idle" : got.version === version ? "ok" : "warn"}">${esc(host.short)} ${esc(got.version)}${!got.enabled ? " · " + t("disabled") : got.version !== version ? " · " + t("older") : ""}</span>`;
  }).join("");
}

/* Evals: the skill rows, each opening in place to its run-all bar and its cases by direction. */
function skillRows(){
  const q = state.q.trim().toLowerCase();
  const rows = DATA.plugins.flatMap(p => p.skills.map(([skill, desc, changed]) => ({p, skill, desc, changed})));
  const counts = {all: rows.length, notrun: 0, noevals: 0};
  const shown = rows.filter(r => {
    r.g = casesOf(r.p, r.skill); r.st = skillStatus(r.p, r.skill, r.changed);
    if (r.st.kind === "notrun") counts.notrun++; if (r.st.kind === "noevals") counts.noevals++;
    if (state.filter !== "all" && r.st.kind !== state.filter) return false;
    if (!q) return true;
    return [r.skill, r.desc, r.p.name, ...r.g.all.map(c => c.name + " " + c.description)].join(" ").toLowerCase().includes(q);
  });
  $("filters").innerHTML = [["all", "fAll"], ["notrun", "fNotRun"], ["noevals", "fNoEvals"]].map(([k, l]) =>
    `<button type="button" class="chip" data-filter="${k}" aria-pressed="${state.filter === k}">${t(l)}<span class="n">${counts[k]}</span></button>`).join("");
  $("skilllist").innerHTML = shown.length ? shown.map(({p, skill, desc, g, st}) => {
    const key = "skill:" + p.name + "/" + skill, open = state.expanded.has(key);
    const cov = [[g.fires.length, t("fires")], [g.quiet.length, t("quiet")], [g.behavior.length, t("behavior")]]
      .map(([n, l]) => `<span class="${n ? "" : "zero"}" title="${esc(l)}">${n}</span>`).join("");
    const latest = Object.entries(st.hosts).map(([host, s]) => `<span class="pill ${s.n && s.pass === s.n && !s.untrusted ? "ok" : s.n || s.untrusted ? "warn" : "idle"}">${esc(hostName(host))} ${fill(t("passOf"), {p: s.pass, n: s.n})}${s.untrusted ? " · " + fill(t("untrustedN"), {k: s.untrusted}) : ""}</span>`).join("");
    return `<div class="skill${open ? " open" : ""}" data-skill="${esc(key)}">
      <div class="skillhead" data-skillhead="${esc(key)}">
        <div><button type="button" class="expander" data-expand="${esc(key)}" aria-expanded="${open}"><b class="mono">${esc(skill)}</b></button><span class="sub">${esc(p.name)} ${esc(p.version || "")}</span></div>
        <div class="goal">${esc(desc)}</div>
        <div class="cov3">${cov}</div>
        <div class="stack status">${st.chips.map(([cls, txt]) => `<span class="pill ${cls}">${esc(txt)}</span>`).join("")}</div>
        <div class="meta">${installedChips(p.name, p.version)}${latest}</div>
      </div>${open ? skillBody(p, skill, key, g) : ""}</div>`;
  }).join("") : `<div class="empty">${t("noMatch")}</div>`;
}
function skillBody(p, skill, key, g){
  if (!g.all.length) return `<div class="skillbody"><span class="muted">${t("noCases")}</span></div>`;
  const label = fill(t("runAllOf"), {n: g.all.length, skill});
  const bar = SERVER ? `<div class="runbar"><div class="row"><b>${esc(label)}</b>
      <button type="button" class="btn ghost small" data-skillrun="${esc(key)}"${JOB.active ? " disabled" : ""}>${t("runAll")}</button></div>
      ${state.skillForm === key ? runFormFor(key, skill, null) : ""}</div>` : "";
  const groups = [["gFires", g.fires], ["gQuiet", g.quiet], ["gBehavior", g.behavior]].filter(([, list]) => list.length);
  return `<div class="skillbody">${bar}${groups.map(([label, list]) =>
    `<div class="group"><span class="eyebrow">${t(label)} (${list.length})</span><div class="caselist">${list.map(c => caseRow(c, key)).join("")}</div></div>`).join("")}</div>`;
}
function caseRow(c, skillKey){
  const sel = state.selected && state.selected.case === keyOf(c) && state.selected.skill === skillKey;
  return `<button type="button" class="caserow" data-case="${esc(keyOf(c))}" data-from="${esc(skillKey)}" aria-current="${!!sel}">
    <span class="cn">${esc(c.name)}</span><span class="tags"><span class="pill ${c.kind === "trigger" ? "trig" : "beh"}">${c.kind}</span>${scorePill(keyOf(c))}</span>
    <span class="cd">${esc(c.description)}</span></button>`;
}

/* The case panel: one case at a time, so each case has exactly one Run form on the page. */
const GTAG = {tool_used: "tool", llm: "llm", regex: "regex", file_exists: "file"};
function graderLine(g){
  let what = g.type === "llm" ? g.rubric : "";
  if (g.type === "tool_used") {
    const target = g.skill ? `Skill ${g.skill}` : g.tool;
    what = g.max === 0 ? `${t("mustNot")} ${target}` : `${t("must")} ${target}`;
    if (!g.skill && g.match) what += ` ${t("matching")} ${g.match}`;
    if (g.tool === "Skill" && g.max !== 0) what += ` — ${t("indicator")}`;
  }
  const tag = GTAG[g.type] || g.type;
  return `<tr><td class="mono">${esc(g.name)}</td><td><span class="gtag ${esc(tag)}">${esc(tag)}</span></td><td>${esc(what)}</td></tr>`;
}
function historyTable(key){
  const h = DATA.results[key] || [];
  if (!h.length) return "";
  return `<div><span class="eyebrow">${t("history")}</span><div class="tw"><table><thead><tr><th>${t("when")}</th><th>${t("host")}</th><th>${t("score")}</th><th>Δ</th><th>${t("runs")}</th><th>${t("note")}</th></tr></thead><tbody>`+
    h.map(r => `<tr><td class="mono">${esc(r.stamp)}</td><td>${esc(hostName(r.host))}${r.model ? " · " + esc(r.model) : ""}</td><td class="num">${f2(r.score)}</td><td class="num">${f2(r.delta)}</td><td class="num">${r.runs}</td><td>${
      esc([r.partial ? `${t("partial")}${r.partialReason ? ": " + r.partialReason : ""}` : "", r.errors.length ? `${t("error")}: ${r.errors.join("; ")}` : "", r.skippedPaid ? t("skippedPaid") : ""].filter(Boolean).join(" · "))}</td></tr>`).join("")+
    `</tbody></table></div></div>`;
}
function casePanel(){
  const sel = state.selected, c = sel && ALL.find(x => keyOf(x) === sel.case);
  if (!c) { $("casepanel").innerHTML = `<span class="muted">${t("pickCase")}</span>`; return; }
  $("casepanel").innerHTML = `<div class="hd"><div><span class="eyebrow">${esc(c.plugin)} · ${c.kind}</span><h3 class="mono">${esc(c.name)}</h3></div>
      <button type="button" class="btn ghost small" data-closepanel="1">${t("closePanel")}</button></div>
    <p class="muted">${esc(c.description)}</p>
    <div class="tags" style="justify-content:flex-start">${scorePill(keyOf(c))}</div>
    <div><span class="eyebrow">${t("prompt")}</span><div class="prompt">${esc(c.prompt)}</div></div>
    <div><span class="eyebrow">${t("graders")} (${c.graders.length})</span><div class="tw"><table><tbody>${c.graders.map(graderLine).join("")}</tbody></table></div></div>
    ${historyTable(keyOf(c))}${SERVER ? runFormFor(keyOf(c), c.name, t("runCase")) : ""}`;
}

/* Run forms, for a case (in the panel) or a skill (in its run bar). Only when served. */
function runFormFor(k, name, title){
  const f = state.form[k] || {host: HOSTS[0].id, arms:"both", model:"", effort:"", cost:"2"};
  const opt = (v, l, cur) => `<option value="${esc(v)}"${v === cur ? " selected" : ""}>${esc(l)}</option>`;
  const armsText = f.arms === "with" ? t("armsWith") : t("armsBoth");
  return `<div>${title ? `<span class="eyebrow">${esc(title)}</span>` : ""}<form class="runform" data-run="${esc(k)}">
    <label>${t("runHost")}<select name="host">${HOSTS.map(h => opt(h.id, h.label, f.host)).join("")}</select></label>
    <label>${t("runArms")}<select name="arms">${opt("both", t("armsBoth"), f.arms)}${opt("with", t("armsWith"), f.arms)}</select></label>
    <label>${t("runModel")}<input type="text" name="model" value="${esc(f.model)}" autocomplete="off" spellcheck="false"></label>
    <label>${t("runEffort")}<select name="effort">${opt("", t("effortDefault"), f.effort)}${["none","minimal","low","medium","high","xhigh","max"].map(e => opt(e, e, f.effort)).join("")}</select></label>
    <label>${t("runCost")}<input type="number" name="cost" min="0.1" max="50" step="0.1" value="${esc(f.cost)}" style="width:6rem"></label>
    <button type="submit" class="btn"${JOB.active ? " disabled" : ""}>${t("start")}</button>
    ${state.confirming === k ? `<div class="confirm"><span>${esc(fill(t("confirmRun"), {case: name, host: hostOf(f.host).label, arms: armsText}))}</span>
      <button type="button" class="btn" data-go="${esc(k)}">${t("confirm")}</button><button type="button" class="btn ghost" data-nogo="1">${t("cancel")}</button></div>` : ""}
  </form></div>`;
}
/* The form that was used: a skill's run-all form and a case's form never share a key, but read the element anyway. */
function formOf(k, el){
  el = el || document.querySelector(`form[data-run="${CSS.escape(k)}"]`);
  if (!el) return state.form[k];
  const fd = new FormData(el), f = {};
  for (const [name, v] of fd.entries()) f[name] = String(v).trim();
  state.form[k] = f; return f;
}

/* The job: polled once a second while it runs. */
const JOB = {active:false, timer:null, last:null, refresh:null, questionId:null, answered:null};
async function api(path, body){
  const res = await fetch(path, {method: body ? "POST" : "GET", headers: {"X-Board-Token": SERVER.token, "Content-Type": "application/json"},
    body: body ? JSON.stringify(body) : undefined});
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || res.statusText);
  return data;
}
function lineKind(l){
  if (l.startsWith("$ ")) return "cmd";
  if (l.startsWith("=== ")) return "sec";
  if (l.startsWith("? ")) return "q";
  if (/^\s+answered: /.test(l)) return "ans";
  if (/^\s+-> score /.test(l)) return "score";
  if (/^\s+\[[^\]]+\] .* -- FAIL\b|^\s+\[[^\]]+\] FAIL -- /.test(l)) return "fail";
  if (/^\s+\[[^\]]+\] pass -- /.test(l)) return "pass";
  if (/^\s+\[[^\]]+\] /.test(l)) return "grader";
  if (/error|exited [1-9]|not graded|could not|stopping:|failed/i.test(l)) return "err";
  return "";
}
function statusLabel(j){
  if (j.question && j.status === "running") return t("sWaiting");
  if (j.status === "running" && j.stopping) return t("sStopping");
  return ({running:t("sRunning"), done:t("sDone"), failed:t("sFailed"), stopped:t("sStopped")})[j.status] || j.status;
}
function renderRun(){
  const j = JOB.last;
  $("runback").textContent = state.back === "install" ? t("backInstall") : t("backEvals");
  $("outputlabel").textContent = t("output");
  if (!j || j.status === "idle") { $("runhead").innerHTML = ""; $("runside").innerHTML = ""; $("runlog").textContent = ""; return; }
  const p = j.progress, cls = j.status === "done" ? "ok" : j.status === "failed" ? "bad" : j.question ? "warn" : "idle";
  $("runhead").innerHTML = `<h2>${esc(j.title)}</h2><span class="pill ${cls}">${esc(statusLabel(j))}</span>
    <span class="pill idle">${esc(hostOf(j.host).label)}${j.model ? " · " + esc(j.model) : ""}</span>
    ${p ? `<span class="muted">${esc(fill(t(j.kind === "eval" ? "caseOf" : "stepOf"), {i: p.index, n: p.total}))}${p.item && p.total > 1 ? ": <b class=\"mono\">" + esc(p.item) + "</b>" : ""}</span>` : ""}
    ${j.maxCostUsd != null ? `<span class="muted">${esc(fill(t("costCeil"), {c: j.maxCostUsd}))}</span>` : ""}
    <span class="spacer"></span>
    ${j.status === "running" ? `<button type="button" class="btn danger" data-stop="1" title="${esc(t("stopHint"))}"${j.stopping ? " disabled" : ""}>${t("stop")}</button>` : ""}`;
  const pct = j.status !== "running" ? 100 : p ? Math.max(3, (p.index - 1) / p.total * 100) : 3;
  $("runbar").style.width = pct + "%";
  let card;
  if (j.question && j.status === "running") {
    const fresh = JOB.questionId !== j.question.id;
    JOB.questionId = j.question.id; if (fresh) JOB.answered = null;
    const off = JOB.answered === j.question.id ? " disabled" : "";
    const b = (c, ico, label) => j.question.choices.includes(c) ? `<button type="button" class="ans ${c}" data-answer="${c}"${off}><span class="ico" aria-hidden="true">${ico}</span>${label}</button>` : "";
    card = `<div class="card"><span class="eyebrow">${t("sWaiting")}</span><div class="question">${esc(j.question.text)}</div>
      <span class="muted">${t("qHint")}</span><div class="answers">${b("y", "✓", t("yes"))}${b("n", "✕", t("no"))}${b("s", "→", t("skip"))}</div></div>`;
  } else {
    const msg = j.status === "running" ? (j.stopping ? t("mStopping") : t("working"))
      : ({done: t("mDone"), stopped: t("mStopped"), failed: t("mFailed")})[j.status] || "";
    card = `<div class="card"><span>${esc(msg)}</span></div>`;
  }
  const files = (j.log || []).map(l => (l.match(/^transcript file: (.+)$/) || [])[1]).filter(Boolean);
  const links = files.length ? files.map(f => `<a class="chip" target="_blank" rel="noopener" href="/transcript?token=${encodeURIComponent(SERVER.token)}&file=${encodeURIComponent(f)}">${esc(f.split("/").pop())}</a>`).join("")
    : `<span class="muted">${t("noTranscripts")}</span>`;
  const tl = j.tally || {};
  const tally = j.kind === "eval" ? `<div class="card"><span class="eyebrow">${t("tally")}</span><div class="tally">
      <span style="color:var(--ok)">✓ <b>${tl.y || 0}</b></span><span style="color:var(--bad)">✕ <b>${tl.n || 0}</b></span><span>→ <b>${tl.s || 0}</b></span></div></div>` : "";
  $("runside").innerHTML = card + (j.kind === "eval" ? `<div class="card"><span class="eyebrow">${t("transcripts")}</span><div class="actions">${links}</div></div>` : "") + tally;
  const log = $("runlog"), atEnd = log.scrollTop + log.clientHeight >= log.scrollHeight - 8;
  log.innerHTML = (j.log || []).map(l => { const k = lineKind(l); return `<span${k ? ` class="l-${k}"` : ""}>${esc(l) || " "}</span>`; }).join("");
  if (atEnd) log.scrollTop = log.scrollHeight;
}
function jobChip(){
  const j = JOB.last, chip = $("jobchip");
  chip.hidden = !j || j.status === "idle" || state.view === "run" || (j.status !== "running" && !j.question);
  if (!chip.hidden) { chip.textContent = fill(t("jobChip"), {s: statusLabel(j), t: j.title}); chip.className = "pill " + (j.question ? "warn" : "idle"); }
}
async function poll(){
  clearTimeout(JOB.timer);
  try {
    const j = await api("/api/job");
    const was = JOB.active; JOB.active = j.status === "running"; JOB.last = j;
    if (state.view === "run") renderRun();
    jobChip(); if (state.view === "install") installTab();
    if (was !== JOB.active) renderEvals();
    if (JOB.active) { JOB.timer = setTimeout(poll, 1000); return; }
    /* A job can end before the first poll sees it running, so refresh on the job we started, not on a change seen. */
    if (was || JOB.refresh) {
      const kind = JOB.refresh || j.kind; JOB.refresh = null;
      setData(await api("/api/state")); if (kind === "install") await loadInstalled(); renderAll();
    }
  } catch (err) { alertRun(err.message); }
}
/* A refused start or a lost connection: shown in the Run view's output, on the last job or a placeholder. */
function alertRun(msg){
  const base = JOB.last && JOB.last.status !== "idle" ? JOB.last : {status:"failed", kind:"eval", title:"", host:(HOSTS[0] || {}).id, log:[]};
  JOB.last = Object.assign({}, base, {log: (base.log || []).concat(msg)});
  if (state.view !== "run") setView("run"); else renderRun();
}

/* Install: the platform buttons, then the chosen host's marketplace card and plugin table. */
async function loadInstalled(){
  if (!SERVER) return;
  try { INSTALLED = await api("/api/installed"); } catch (err) { INSTALLED = {error: err.message}; }
}
function commandText(host, action, plugin, source){
  const exe = hostOf(host).exe;
  if (action === "marketplace-add") return `${exe} plugin marketplace add ${source === "checkout" ? "<this checkout>" : "eurus-labs/Skills"}`;
  if (action === "marketplace-update") return `${exe} plugin marketplace update eurus-labs`;
  return (Array.isArray(plugin) ? plugin : [plugin]).map(p => `${exe} plugin ${action} ${p}@eurus-labs`).join("\n");
}
function hostStatus(id){
  const h = INSTALLED && !INSTALLED.error ? INSTALLED[id] : null;
  if (!h) return {dot: "off", text: INSTALLED ? "—" : t("loading")};
  if (!h.available) return {dot: "off", text: t("notFound")};
  const n = DATA.plugins.length, k = DATA.plugins.filter(p => h.plugins[p.name]).length;
  if (!h.marketplace) return {dot: "warn", text: t("notRegistered")};
  return {dot: k === n ? "ok" : "warn", text: fill(t("nInstalled"), {k, n})};
}
function headerHosts(){
  $("hoststatus").innerHTML = SERVER ? HOSTS.map(h => { const s = hostStatus(h.id);
    return `<span class="pill idle" title="${esc(h.label)}: ${esc(s.text)}"><span class="dot ${s.dot}"></span>${esc(h.short)}</span>`; }).join("") : "";
}
function installTab(){
  if (!SERVER) return;
  if (!state.platform || !HOSTS.some(h => h.id === state.platform)) {
    const avail = HOSTS.find(h => INSTALLED && INSTALLED[h.id] && INSTALLED[h.id].available);
    state.platform = (avail || HOSTS[0]).id;
  }
  $("platforms").innerHTML = HOSTS.map(h => { const s = hostStatus(h.id);
    return `<button type="button" class="platform" data-platform="${esc(h.id)}" aria-pressed="${state.platform === h.id}"><b><span class="dot ${s.dot}"></span>${esc(h.label)}</b><span>${esc(s.text)}</span></button>`; }).join("");
  const c = state.installing, j = JOB.last;
  $("installconfirm").innerHTML = c ? `<div class="confirm"><span>${t("willRun")}</span><span class="cmd">${esc(commandText(c.host, c.action, c.plugins, c.source))}</span>
      <button type="button" class="btn" data-installgo="1"${JOB.active ? " disabled" : ""}>${t("confirm")}</button><button type="button" class="btn ghost" data-installno="1">${t("cancel")}</button></div>`
    : j && j.kind === "install" && j.status === "running" ? `<div class="notice"><span>${esc(fill(t("installRunning"), {t: j.title}))}…</span><button type="button" class="btn ghost small" data-showrun="1">${t("showOutput")}</button></div>` : "";
  const body = $("installbody"), host = hostOf(state.platform);
  if (!INSTALLED) { body.innerHTML = `<span class="muted">${t("loading")}</span>`; return; }
  if (INSTALLED.error) { body.innerHTML = `<span class="pill bad">${esc(INSTALLED.error)}</span>`; return; }
  const h = INSTALLED[host.id] || {};
  const refresh = `<button type="button" class="btn ghost small" data-refresh="1">${t("refresh")}</button>`;
  if (!h.available) { body.innerHTML = `<div class="card"><b>${esc(host.label)}</b><span>${esc(fill(t("fixPath"), {label: host.label, exe: host.exe}))}</span><div class="actions">${refresh}</div></div>`; return; }
  const busy = JOB.active ? " disabled" : "";
  const b = (action, label, extra, off) => `<button type="button" class="btn ghost small" data-install="${action}" data-host="${esc(host.id)}" ${extra || ""}${busy || (off ? " disabled" : "")}>${label}</button>`;
  const market = `<div class="card"><span class="eyebrow">${t("marketplace")}</span>
    <span>${h.marketplace ? `<span class="cmd">${esc(h.marketplace)}</span>` : `<span class="pill warn">${t("notRegistered")}</span> <span class="muted">${t("registerFirst")}</span>`}</span>
    ${h.error ? `<span class="pill warn" title="${esc(h.error)}">${esc(h.error.slice(0, 100))}</span>` : ""}
    <div class="actions">${b("marketplace-add", t("fromCheckout"), 'data-source="checkout"')}${b("marketplace-add", t("fromGithub"), 'data-source="github"')}${h.marketplace ? b("marketplace-update", t("updateMarket")) : ""}${refresh}</div></div>`;
  const noMarket = !h.marketplace;
  /* Fixed slots: Install or Update always first, Uninstall always second, so the buttons line up on every row. */
  const slots = p => {
    const got = h.plugins[p.name];
    const one = b(got ? "update" : "install", got ? t("update") : t("install"), `data-iplugin="${esc(p.name)}"`, noMarket);
    const two = got ? b("uninstall", t("uninstall"), `data-iplugin="${esc(p.name)}"`, noMarket)
      : `<button type="button" class="btn ghost small hold" tabindex="-1" aria-hidden="true" disabled>${t("uninstall")}</button>`;
    return `<div class="slots">${one}${two}</div>`;
  };
  const chip = p => { const got = h.plugins[p.name];
    if (!got) return `<span class="pill missing">${t("notInstalled")}</span>`;
    if (!got.enabled) return `<span class="pill idle">${esc(got.version)} · ${t("disabled")}</span>`;
    return got.version === p.version ? `<span class="pill ok">${esc(got.version)}</span>` : `<span class="pill warn">${esc(got.version)} · ${t("older")}</span>`; };
  body.innerHTML = market + `<div class="grid"><table><thead><tr><th>${t("colPlugin")}</th><th>${t("colHere")}</th><th>${esc(fill(t("colIn"), {host: host.label}))}</th>
      <th><div class="slots">${b("install", t("installAll"), 'data-all="1"', noMarket)}${b("update", t("updateAll"), 'data-all="1"', noMarket)}</div></th></tr></thead><tbody>${
    DATA.plugins.map(p => `<tr><td><b class="mono">${esc(p.name)}</b><span class="sub">${p.skills.map(s => esc(s[0])).join(", ")}</span></td>
      <td class="mono">${esc(p.version || "")}</td><td>${chip(p)}</td><td>${slots(p)}</td></tr>`).join("")}</tbody></table></div>`;
}

function renderEvals(){ stats(); skillRows(); casePanel(); }
function renderAll(){ renderEvals(); headerHosts(); installTab(); jobChip(); if (state.view === "run") renderRun(); }
function setView(view){
  if (view === "install" && !SERVER) view = "evals";
  if (view !== "run") { state.back = view; try { localStorage.setItem("eval-board-tab", view); } catch (e) {} }
  state.view = view;
  document.querySelectorAll("[data-tab]").forEach(b => b.setAttribute("aria-selected", b.dataset.tab === view));
  document.querySelectorAll("[data-view]").forEach(p => { p.hidden = p.dataset.view !== view; });
  if (view === "run") renderRun();
  if (view === "install") installTab();
  jobChip();
}
function applyLang(){
  document.documentElement.lang = lang;
  document.querySelectorAll("[data-i18n]").forEach(el => { el.textContent = t(el.dataset.i18n); });
  document.querySelectorAll("[data-lang]").forEach(b => b.setAttribute("aria-pressed", b.dataset.lang === lang));
  const title = SERVER ? t("titleManager") : t("title");
  $("title").textContent = title; document.title = title;
  $("tab-install").textContent = t("tabInstall"); $("tab-evals").textContent = t("tabEvals");
  $("tab-install").hidden = !SERVER;
  $("q").placeholder = t("search"); $("q").setAttribute("aria-label", t("search"));
  $("runhint").textContent = SERVER ? "" : t("runHint");
  renderAll();
}

document.addEventListener("submit", e => {
  const form = e.target.closest("form[data-run]"); if (!form) return;
  e.preventDefault(); const k = form.dataset.run; formOf(k, form); state.confirming = k; renderEvals();
});
document.addEventListener("change", e => { const form = e.target.closest("form[data-run]"); if (form) formOf(form.dataset.run, form); });
document.addEventListener("click", async e => {
  const el = sel => e.target.closest(sel);
  const l = el("[data-lang]"); if (l) { lang = l.dataset.lang; try { localStorage.setItem("eval-board-lang", lang); } catch (err) {} applyLang(); return; }
  const tab = el("[data-tab]"); if (tab) { setView(tab.dataset.tab); return; }
  const f = el("[data-filter]"); if (f) { state.filter = f.dataset.filter; skillRows(); return; }
  const cr = el("[data-case]");
  if (cr) {
    state.selected = {case: cr.dataset.case, skill: cr.dataset.from}; state.confirming = null; skillRows(); casePanel();
    if (window.matchMedia("(max-width:1060px)").matches) $("casepanel").scrollIntoView({behavior: "smooth", block: "start"});
    return;
  }
  if (el("[data-closepanel]")) { state.selected = null; skillRows(); casePanel(); return; }
  /* A click anywhere on a skill's header opens or closes it, except on its own controls. */
  const head = el("[data-skillhead]");
  if (head && (el("[data-expand]") || !el("button,a,input,select,label"))) {
    const k = head.dataset.skillhead;
    if (state.expanded.has(k)) { state.expanded.delete(k); if (state.skillForm === k) state.skillForm = null; } else state.expanded.add(k);
    skillRows(); return;
  }
  if (el("#runback")) { setView(state.back); return; }
  if (el("#jobchip") || el("[data-showrun]")) { setView("run"); return; }
  if (!SERVER) return;
  const sr = el("[data-skillrun]");
  if (sr) { const k = sr.dataset.skillrun; state.skillForm = state.skillForm === k ? null : k; state.confirming = null; skillRows(); return; }
  if (el("[data-nogo]")) { state.confirming = null; renderEvals(); return; }
  const go = el("[data-go]");
  if (go) {
    const k = go.dataset.go, f = formOf(k, go.closest("form")) || {};
    state.confirming = null;
    const opts = {host: f.host || HOSTS[0].id, arms: f.arms || "both", model: f.model || "", effort: f.effort || "", max_cost_usd: parseFloat(f.cost || "2")};
    try {
      if (k.startsWith("skill:")) {
        const [plugin, skill] = k.slice(6).split("/"), p = DATA.plugins.find(x => x.name === plugin);
        await api("/api/run", Object.assign({plugin, cases: p.cases.filter(c => c.skills.includes(skill)).map(c => c.name), label: skill}, opts));
        state.skillForm = null;
      } else {
        const [plugin, ...rest] = k.split("/");
        await api("/api/run", Object.assign({plugin, case: rest.join("/")}, opts));
      }
      JOB.refresh = "eval"; JOB.questionId = null; JOB.answered = null; state.back = "evals"; setView("run"); poll();
    } catch (err) { alertRun(err.message); }
    renderEvals(); return;
  }
  const ans = el("[data-answer]");
  if (ans) {
    /* One answer per question: the buttons stay disabled until the next question arrives. */
    const id = JOB.questionId; if (id == null || JOB.answered === id) return;
    JOB.answered = id; document.querySelectorAll("[data-answer]").forEach(b => { b.disabled = true; });
    try { await api("/api/answer", {id, reply: ans.dataset.answer}); poll(); } catch (err) { alertRun(err.message); }
    return;
  }
  if (el("[data-stop]")) { el("[data-stop]").disabled = true; try { await api("/api/stop", {}); poll(); } catch (err) { alertRun(err.message); } return; }
  const pf = el("[data-platform]"); if (pf) { state.platform = pf.dataset.platform; state.installing = null; installTab(); return; }
  const ins = el("[data-install]");
  if (ins) {
    const host = ins.dataset.host, action = ins.dataset.install;
    const plugins = ins.dataset.all ? DATA.plugins.map(p => p.name) : ins.dataset.iplugin ? [ins.dataset.iplugin] : null;
    state.installing = {host, action, plugins, source: ins.dataset.source}; installTab();
    window.scrollTo({top: $("installconfirm").offsetTop - 80, behavior: "smooth"}); return;
  }
  if (el("[data-installno]")) { state.installing = null; installTab(); return; }
  if (el("[data-installgo]")) {
    const c = state.installing; state.installing = null;
    try { await api("/api/install", c.plugins ? {host: c.host, action: c.action, plugins: c.plugins} : {host: c.host, action: c.action, source: c.source});
      JOB.refresh = "install"; poll(); }
    catch (err) { alertRun(err.message); }
    installTab(); return;
  }
  if (el("[data-refresh]")) { INSTALLED = null; renderAll(); await loadInstalled(); renderAll(); }
});
$("q").addEventListener("input", e => { state.q = e.target.value; skillRows(); });

let saved = "evals";
/* An older page saved "skills", the tab that folded into Evals. */
try { if (localStorage.getItem("eval-board-tab") === "install") saved = "install"; } catch (e) {}
applyLang();
setView(saved);
if (SERVER) { poll(); loadInstalled().then(renderAll); }
</script>
</body>
</html>
"""

if __name__ == "__main__":
    sys.exit(main())
