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


def skills_of(plugin_dir):
    """[(skill, one-line description)] in the order the plugin's manifest lists them."""
    manifest = json.loads(read(os.path.join(plugin_dir, ".github", "plugin", "plugin.json")))
    found = []
    for entry in manifest.get("skills", []):
        name = os.path.basename(entry.rstrip("/"))
        fields, _ = frontmatter(read(os.path.join(plugin_dir, entry, "SKILL.md")))
        description = unquote(fields.get("description", ""))
        found.append((name, short(description)))
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
        names = [s for s, _ in skills]
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
        plugins.append({"name": plugin, "skills": skills, "cases": cases})
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


def board(plugins, results):
    data = {"plugins": plugins, "results": results}
    payload = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
    return PAGE.replace("__DATA__", payload)


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
/* A run sheet per skill: the summary first, then one block per skill, then every case. */
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
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 var(--sans)}
.wrap{max-width:1120px;margin:0 auto;padding:28px 16px 64px;display:flex;flex-direction:column;gap:32px}
h1,h2,h3{margin:0;line-height:1.25;text-wrap:balance} h1{font-size:1.9rem} h2{font-size:1.3rem} h3{font-size:1.05rem}
p{margin:0;max-width:72ch}
.mono,code{font-family:var(--mono);font-size:.86em}
.eyebrow{font-family:var(--mono);font-size:.74rem;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
.muted{color:var(--muted)}
header{display:flex;flex-wrap:wrap;gap:12px;justify-content:space-between;align-items:flex-start}
header .t{display:flex;flex-direction:column;gap:8px;min-width:0;flex:1 1 420px}
.lang{display:flex;border:1px solid var(--line);border-radius:999px;overflow:hidden;background:var(--panel)}
.lang button{font:inherit;font-size:.85rem;border:0;background:transparent;color:var(--ink);padding:6px 14px;cursor:pointer}
.lang button[aria-pressed="true"]{background:var(--accent);color:var(--panel)}
button:focus-visible,summary:focus-visible,input:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
section{display:flex;flex-direction:column;gap:14px}
.stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}
@media (max-width:760px){.stats{grid-template-columns:repeat(2,minmax(0,1fr))}}
.stat{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px 14px;display:flex;flex-direction:column}
.stat b{font-size:1.7rem;font-variant-numeric:tabular-nums} .stat span{color:var(--muted);font-size:.85rem}
.stat.alert{border-color:var(--warn);background:var(--warn-soft)} .stat.alert b{color:var(--warn)}
.skills{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:12px}
@media (max-width:400px){.skills{grid-template-columns:minmax(0,1fr)}}
.skill{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px 16px;display:flex;flex-direction:column;gap:10px;min-width:0}
.skill .hd{display:flex;justify-content:space-between;gap:8px;align-items:baseline;flex-wrap:wrap}
.skill .desc{font-size:.86rem;color:var(--muted)}
.cov{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;font-size:.8rem}
.cov div{background:var(--bg);border-radius:8px;padding:6px 8px;display:flex;flex-direction:column}
.cov b{font-size:1.15rem;font-variant-numeric:tabular-nums}
.cov .zero b{color:var(--bad)}
.rows{display:flex;flex-direction:column;gap:4px}
.row{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:8px;font-size:.82rem;align-items:center}
.row .n{font-family:var(--mono);overflow-wrap:anywhere}
.pill{display:inline-flex;gap:6px;font-family:var(--mono);font-size:.72rem;padding:2px 8px;border-radius:999px;white-space:nowrap;border:1px solid transparent}
.pill.ok{background:var(--ok-soft);color:var(--ok)} .pill.warn{background:var(--warn-soft);color:var(--warn)}
.pill.bad{background:var(--bad-soft);color:var(--bad)} .pill.idle{color:var(--muted);border-color:var(--line)}
.pill.trig{background:var(--trig-soft);color:var(--trig)} .pill.beh{background:var(--beh-soft);color:var(--beh)}
.pill.quiet{background:var(--bg);color:var(--muted)}
.pill .host{font-weight:600;margin-right:2px}
.controls{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.chip{font:inherit;font-size:.84rem;padding:5px 12px;border-radius:999px;border:1px solid var(--line);background:var(--panel);color:var(--ink);cursor:pointer}
.chip[aria-pressed="true"]{background:var(--accent);border-color:var(--accent);color:var(--panel)}
input[type=search]{font:inherit;font-size:.88rem;padding:6px 12px;border-radius:8px;border:1px solid var(--line);background:var(--panel);color:var(--ink);flex:1 1 220px;min-width:0}
.cases{display:flex;flex-direction:column;border:1px solid var(--line);border-radius:10px;background:var(--panel);overflow:hidden}
details.case{border-top:1px solid var(--line)} details.case:first-child{border-top:0}
details.case summary{list-style:none;cursor:pointer;display:grid;grid-template-columns:minmax(0,1fr) auto;gap:4px 12px;padding:12px 16px;align-items:center}
details.case summary::-webkit-details-marker{display:none}
.cn{font-family:var(--mono);font-size:.88rem;font-weight:600;overflow-wrap:anywhere}
.cd{grid-column:1/-1;color:var(--muted);font-size:.85rem}
.tags{display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end}
@media (max-width:560px){details.case summary{grid-template-columns:minmax(0,1fr)}.tags{justify-content:flex-start}}
.body{padding:0 16px 16px;display:flex;flex-direction:column;gap:12px}
.prompt{font-family:var(--mono);font-size:.8rem;background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:10px 12px;white-space:pre-wrap;overflow-wrap:anywhere}
table{border-collapse:collapse;width:100%;font-size:.82rem} th,td{text-align:left;padding:5px 8px;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--muted);font-weight:500} td.num{font-family:var(--mono);font-variant-numeric:tabular-nums}
.tw{overflow-x:auto}
.empty{padding:18px 16px;color:var(--muted)}
.foot{color:var(--muted);font-size:.82rem}
</style>
</head>
<body>
<div class="wrap">
<header>
  <div class="t">
    <span class="eyebrow">claude plugin eval</span>
    <h1 data-i18n="title"></h1>
    <p data-i18n="lede"></p>
  </div>
  <div class="lang" role="group" aria-label="Language">
    <button type="button" data-lang="en">English</button><button type="button" data-lang="vi">Tiếng Việt</button>
  </div>
</header>
<section><div class="stats" id="stats"></div><p class="foot" id="trustnote"></p></section>
<section><h2 data-i18n="bySkill"></h2><p class="muted" data-i18n="bySkillLede"></p><div class="skills" id="skills"></div></section>
<section>
  <h2 data-i18n="allCases"></h2>
  <div class="controls" id="pchips"></div>
  <div class="controls"><div class="controls" id="kchips"></div><input type="search" id="q" aria-label="Search"></div>
  <div class="cases" id="cases"></div>
</section>
<p class="foot" data-i18n="foot"></p>
</div>
<script>
const DATA = __DATA__;
const T = {
 en:{title:"Skills eval board",
  lede:"Every eval case in this repository, grouped by the skill it tests, with the latest local run of each on Claude Code and on Copilot CLI, kept apart. A case's score is its with-plugin score; Δ is how far that is above the run without the plugin.",
  cases:"eval cases", skillsCovered:"skills with a case", trusted:"cases with a trusted score", files:"result files read",
  trustnote:"A score counts as trusted only when the suite finished and no run of the case ended in an error. Partial suites (cost ceiling, interrupted, failed sign-in) are shown but never trusted.",
  bySkill:"By skill", bySkillLede:"Fires: cases where the skill must be called. Quiet: cases where it must not be. Behavior: cases that grade what it does. A zero means that direction is untested.",
  fires:"fires", quiet:"quiet", behavior:"behavior", noCases:"No eval cases yet.",
  allCases:"All cases", allPlugins:"All plugins", allKinds:"All kinds", search:"Search name, description, prompt…",
  notRun:"not run", untrusted:"untrusted", run:"run", runs:"runs", with:"with", delta:"Δ",
  prompt:"Prompt sent to the agent", graders:"Graders", history:"Runs", when:"Run", score:"Score", note:"Note",
  partial:"partial", error:"error", skippedPaid:"judge graders skipped", none:"No case matches the filters.",
  indicator:"plugin-fired indicator, not scored", mustNot:"must not call", must:"must call",
  matching:"with input matching", lastTrusted:"last trusted", host:"Host",
  foot:"Generated by tools/build_eval_board.py from plugins/*/evals and the git-ignored plugins/*/evals/results/. Re-run it after each eval run."},
 vi:{title:"Bảng eval của các skill",
  lede:"Mọi case eval trong repo, gom theo skill mà nó kiểm, kèm lần chạy local mới nhất của từng case trên Claude Code và trên Copilot CLI, tách riêng từng host. Điểm của case là điểm khi có plugin; Δ là chênh lệch so với lượt chạy không có plugin.",
  cases:"case eval", skillsCovered:"skill có case", trusted:"case có điểm tin được", files:"file kết quả đã đọc",
  trustnote:"Điểm chỉ được tin khi cả suite chạy xong và không lượt nào của case bị lỗi. Suite dở dang (chạm trần chi phí, bị ngắt, đăng nhập lỗi) vẫn hiện nhưng không bao giờ được tin.",
  bySkill:"Theo skill", bySkillLede:"Phải gọi: case mà skill phải được gọi. Phải im: case mà skill không được gọi. Hành vi: case chấm việc skill làm. Số 0 nghĩa là chiều đó chưa được kiểm.",
  fires:"phải gọi", quiet:"phải im", behavior:"hành vi", noCases:"Chưa có case eval nào.",
  allCases:"Tất cả case", allPlugins:"Mọi plugin", allKinds:"Mọi loại", search:"Tìm theo tên, mô tả, câu hỏi…",
  notRun:"chưa chạy", untrusted:"không tin được", run:"lượt", runs:"lượt", with:"có plugin", delta:"Δ",
  prompt:"Câu hỏi gửi agent", graders:"Grader", history:"Các lần chạy", when:"Lần chạy", score:"Điểm", note:"Ghi chú",
  partial:"dở dang", error:"lỗi", skippedPaid:"bỏ qua grader dùng model", none:"Không có case nào khớp bộ lọc.",
  indicator:"chỉ báo plugin được gọi, không tính điểm", mustNot:"không được gọi", must:"phải gọi",
  matching:"với input khớp", lastTrusted:"tin được gần nhất", host:"Host",
  foot:"Sinh bởi tools/build_eval_board.py từ plugins/*/evals và thư mục plugins/*/evals/results/ (bị git bỏ qua). Chạy lại sau mỗi lần chạy eval."}
};
let lang = "en";
try { const saved = localStorage.getItem("eval-board-lang"); if (saved === "vi" || saved === "en") lang = saved; } catch (e) {}
const state = {plugin:"all", kind:"all", q:""};
const t = k => T[lang][k];
const esc = s => String(s == null ? "" : s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const $ = id => document.getElementById(id);
const ALL = DATA.plugins.flatMap(p => p.cases.map(c => Object.assign({plugin:p.name}, c)));
const trusted = r => r.score != null && !r.partial && !r.errors.length && !r.skippedPaid;
const keyOf = c => c.plugin + "/" + c.name;
const f2 = v => v == null ? "—" : (+v).toFixed(2);

function scored(r){
  const cls = r.score >= 0.8 ? "ok" : r.score >= 0.5 ? "warn" : "bad";
  const d = r.delta == null ? "" : ` · Δ ${r.delta >= 0 ? "+" : ""}${(+r.delta).toFixed(2)}`;
  return [cls, `${f2(r.score)}${d}`];
}

/* One badge per host, never mixed: a skill can trigger on Claude and stay silent on Copilot.
   Each badge is that host's newest run. When it cannot be trusted, the host's last trusted score
   follows it, labelled as such, so an old pass never stands in for a newer failure. */
const HOSTS = ["claude", "copilot"];
const hostName = h => ({claude: "Claude", copilot: "Copilot"})[h] || h;
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
  const hosts = [...HOSTS, ...new Set(all.map(r => r.host))].filter((v, i, a) => a.indexOf(v) === i);
  return hosts.map(host => { const h = all.filter(r => r.host === host); return h.length ? hostPill(host, h) : ""; }).join("");
}

function stats(){
  const skills = DATA.plugins.flatMap(p => p.skills.map(s => s[0]));
  const covered = new Set(ALL.flatMap(c => c.skills));
  const scored = ALL.filter(c => (DATA.results[keyOf(c)] || []).some(trusted)).length;
  const files = new Set(Object.values(DATA.results).flat().map(r => r.stamp)).size;
  $("stats").innerHTML =
    `<div class="stat"><b>${ALL.length}</b><span>${t("cases")}</span></div>`+
    `<div class="stat"><b>${skills.filter(s => covered.has(s)).length} / ${skills.length}</b><span>${t("skillsCovered")}</span></div>`+
    `<div class="stat ${scored ? "" : "alert"}"><b>${scored}</b><span>${t("trusted")}</span></div>`+
    `<div class="stat"><b>${files}</b><span>${t("files")}</span></div>`;
  $("trustnote").textContent = t("trustnote");
}

function skillCards(){
  const cards = DATA.plugins.flatMap(p => p.skills.map(s => [p, s]))
    .sort((a, b) => (b[0].cases.some(c => c.skills.includes(b[1][0])) ? 1 : 0) - (a[0].cases.some(c => c.skills.includes(a[1][0])) ? 1 : 0));
  $("skills").innerHTML = cards.map(([p, [skill, desc]]) => {
    const mine = p.cases.filter(c => c.skills.includes(skill));
    const fire = mine.filter(c => c.kind === "trigger" && c.fires.includes(skill));
    const quiet = mine.filter(c => c.kind === "trigger" && !c.fires.includes(skill));
    const beh = mine.filter(c => c.kind === "behavior");
    const cell = (n, k) => `<div class="${n ? "" : "zero"}"><b>${n}</b>${t(k)}</div>`;
    const rows = mine.length ? mine.map(c => `<div class="row"><span class="n">${esc(c.name)}</span>${scorePill(p.name + "/" + c.name)}</div>`).join("")
      : `<span class="muted">${t("noCases")}</span>`;
    return `<article class="skill"><div class="hd"><h3 class="mono">${esc(skill)}</h3><span class="pill idle">${esc(p.name)}</span></div>
      <p class="desc">${esc(desc)}</p>
      <div class="cov">${cell(fire.length, "fires")}${cell(quiet.length, "quiet")}${cell(beh.length, "behavior")}</div>
      <div class="rows">${rows}</div></article>`;
  }).join("");
}

function chips(){
  const plugins = ["all", ...DATA.plugins.filter(p => p.cases.length).map(p => p.name)];
  $("pchips").innerHTML = plugins.map(p => `<button type="button" class="chip" data-plugin="${p}" aria-pressed="${state.plugin === p}">${p === "all" ? t("allPlugins") : esc(p)}</button>`).join("");
  $("kchips").innerHTML = [["all", t("allKinds")], ["trigger", "trigger"], ["behavior", "behavior"]]
    .map(([k, l]) => `<button type="button" class="chip" data-kind="${k}" aria-pressed="${state.kind === k}">${l}</button>`).join("");
  $("q").placeholder = t("search");
}

function graderLine(g){
  let what = g.type;
  if (g.type === "tool_used") {
    const target = g.skill ? `Skill ${g.skill}` : g.tool;
    what = g.max === 0 ? `${t("mustNot")} ${target}` : `${t("must")} ${target}`;
    if (!g.skill && g.match) what += ` ${t("matching")} ${g.match}`;
    if (g.tool === "Skill" && g.max !== 0) what += ` — ${t("indicator")}`;
  }
  const rubric = g.type === "llm" ? g.rubric : "";
  return `<tr><td class="mono">${esc(g.name)}</td><td class="mono">${esc(g.type)}</td><td>${esc(g.type === "tool_used" ? what : rubric)}</td></tr>`;
}

function historyTable(key){
  const h = DATA.results[key] || [];
  if (!h.length) return "";
  return `<div><span class="eyebrow">${t("history")}</span><div class="tw"><table><thead><tr><th>${t("when")}</th><th>${t("host")}</th><th>${t("score")}</th><th>Δ</th><th>${t("runs")}</th><th>${t("note")}</th></tr></thead><tbody>`+
    h.map(r => `<tr><td class="mono">${esc(r.stamp)}</td><td>${esc(hostName(r.host))}${r.model ? " · " + esc(r.model) : ""}</td><td class="num">${f2(r.score)}</td><td class="num">${f2(r.delta)}</td><td class="num">${r.runs}</td><td>${
      esc([r.partial ? `${t("partial")}${r.partialReason ? ": " + r.partialReason : ""}` : "", r.errors.length ? `${t("error")}: ${r.errors.join("; ")}` : "", r.skippedPaid ? t("skippedPaid") : ""].filter(Boolean).join(" · "))}</td></tr>`).join("")+
    `</tbody></table></div></div>`;
}

function render(){
  document.querySelectorAll("[data-plugin]").forEach(b => b.setAttribute("aria-pressed", b.dataset.plugin === state.plugin));
  document.querySelectorAll("[data-kind]").forEach(b => b.setAttribute("aria-pressed", b.dataset.kind === state.kind));
  const q = state.q.toLowerCase();
  const list = ALL.filter(c => (state.plugin === "all" || c.plugin === state.plugin) && (state.kind === "all" || c.kind === state.kind)
    && (!q || (c.name + " " + c.description + " " + c.prompt).toLowerCase().includes(q)));
  $("cases").innerHTML = list.length ? list.map(c => `<details class="case"><summary><span class="cn">${esc(c.name)}</span>
      <span class="tags"><span class="pill idle">${esc(c.plugin)}</span><span class="pill ${c.kind === "trigger" ? "trig" : "beh"}">${c.kind}</span>${scorePill(keyOf(c))}</span>
      <span class="cd">${esc(c.description)}</span></summary>
      <div class="body"><div><span class="eyebrow">${t("prompt")}</span><div class="prompt">${esc(c.prompt)}</div></div>
      <div><span class="eyebrow">${t("graders")} (${c.graders.length})</span><div class="tw"><table><tbody>${c.graders.map(graderLine).join("")}</tbody></table></div></div>
      ${historyTable(keyOf(c))}</div></details>`).join("") : `<div class="empty">${t("none")}</div>`;
}

function applyLang(){
  document.documentElement.lang = lang;
  document.querySelectorAll("[data-i18n]").forEach(el => { el.textContent = t(el.dataset.i18n); });
  document.querySelectorAll("[data-lang]").forEach(b => b.setAttribute("aria-pressed", b.dataset.lang === lang));
  stats(); skillCards(); chips(); render();
}

document.addEventListener("click", e => {
  const l = e.target.closest("[data-lang]");
  if (l) { lang = l.dataset.lang; try { localStorage.setItem("eval-board-lang", lang); } catch (err) {} applyLang(); }
  const p = e.target.closest("[data-plugin]"); if (p) { state.plugin = p.dataset.plugin; render(); }
  const k = e.target.closest("[data-kind]"); if (k) { state.kind = k.dataset.kind; render(); }
});
$("q").addEventListener("input", e => { state.q = e.target.value; render(); });
applyLang();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    sys.exit(main())
