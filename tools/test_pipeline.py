#!/usr/bin/env python3
"""Behavioural tests for select_units.py and pipeline.py.

Stdlib only, no test framework -- see tools/test_check_env.py for why.

The driver's whole value is that it does not lose things: not an exit code, not a stage,
not a claim somebody wrote by hand. So the tests here are about what a driver gets wrong.
It must stop at the first failure rather than running on; it must pass the failing stage's
exit code out unchanged, because converting a verdict into a different number is the same
as hiding it; it must skip a stage whose input was never written instead of failing; and
the two stages allowed to fail must not take their component down with them.

    python3 tools/test_pipeline.py
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

from component_scripts import component_paths, script

sys.path[:0] = component_paths()
import pipeline

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE = os.path.join(REPO, "tests", "contracts", "flow-repo")

FAILURES = []


def check(name, condition, detail=""):
    if condition:
        print("ok   %s" % name)
    else:
        print("FAIL %s %s" % (name, detail))
        FAILURES.append(name)


def run(name, *args, **kwargs):
    proc = subprocess.run([sys.executable, script(name)] + list(args),
                          capture_output=True, text=True, cwd=kwargs.get("cwd"))
    return proc.returncode, proc.stdout + proc.stderr


def write(path, text):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def units_tests(tmp):
    """select_units.py: the cutoff, the tie-break, and the warning that it is a bad one."""
    index_path = os.path.join(tmp, "structure.json")
    root = os.path.join(tmp, "repo")
    shutil.copytree(FIXTURE, root)
    run("scan_repo.py", "--root", root, "--out", index_path, "--detail")

    out = os.path.join(tmp, "units.txt")
    code, text = run("select_units.py", "--index", index_path, "--out", out)
    check("select_units exits 0 on a real index", code == 0, text)
    selected = [l.strip() for l in open(out, encoding="utf-8") if l.strip()]
    check("select_units keeps the depended-upon modules",
          "src/pipeline/transform.py" in selected and "src/pipeline/store.py" in selected,
          str(selected))
    check("select_units adds the entry point despite fan-in 0",
          "src/pipeline/entry.py" in selected, str(selected))
    check("select_units names why each unit is in the list",
          "entry_point" in text and "connected" in text, text)

    # The orchestrator case, shaped like requests: `session.py` imports four modules and
    # one module imports it; `compat.py` is imported by four and imports nothing; `flags.py`
    # is imported by two. By fan-in alone a cutoff of 2 took compat and flags and dropped
    # the module the request path runs through.
    def mod(path):
        return {"path": path, "lang": "python", "symbols": [{"name": "x", "line": 1}]}
    names = ["pkg/api.py", "pkg/session.py", "pkg/compat.py", "pkg/flags.py",
             "pkg/models.py", "pkg/adapter.py", "pkg/hooks.py"]
    edges = [("pkg/api.py", "pkg/session.py"),
             ("pkg/session.py", "pkg/models.py"), ("pkg/session.py", "pkg/adapter.py"),
             ("pkg/session.py", "pkg/hooks.py"), ("pkg/session.py", "pkg/compat.py"),
             ("pkg/models.py", "pkg/compat.py"), ("pkg/adapter.py", "pkg/compat.py"),
             ("pkg/hooks.py", "pkg/compat.py"),
             ("pkg/models.py", "pkg/flags.py"), ("pkg/adapter.py", "pkg/flags.py")]
    synthetic = {"schema_version": 3, "files": [mod(n) for n in names],
                 "edges": [{"from": a, "to": b, "line": 1} for a, b in edges],
                 "entry_points": []}
    shaped = os.path.join(tmp, "orchestrator.json")
    with open(shaped, "w", encoding="utf-8") as fh:
        json.dump(synthetic, fh)
    code, text = run("select_units.py", "--index", shaped, "--out", out, "--top", "2")
    chosen = [l.strip() for l in open(out, encoding="utf-8") if l.strip()]
    check("a module the system runs through outranks a leaf helper at a tight cutoff",
          code == 0 and chosen == ["pkg/compat.py", "pkg/session.py"], str(chosen) + text)

    # A cutoff of zero still keeps the entry points: they are added, not ranked.
    code, _ = run("select_units.py", "--index", index_path, "--out", out, "--top", "0")
    kept = [l.strip() for l in open(out, encoding="utf-8") if l.strip()]
    check("--top 0 keeps only the entry points",
          code == 0 and kept == ["src/pipeline/entry.py"], str(kept))

    # A file that defines nothing cannot be described. `validate_analysis` wants a
    # statement naming something in the module, and `assemble` wants a fragment citing a
    # derived claim; an empty `__init__.py` offers neither. Selecting one puts a unit in
    # the budget that no work can satisfy -- the assembler then fails the run for a unit
    # with no row, which is how a package marker stopped a document being built at all.
    run("scan_repo.py", "--root", root, "--out", index_path, "--detail")
    with open(index_path, encoding="utf-8") as fh:
        scanned = json.load(fh)
    # Not "the file is empty": a package marker usually carries a docstring and still
    # defines nothing, which is the condition that matters here.
    check("the fixture holds a module that defines nothing",
          any(not r.get("symbols") for r in scanned["files"]),
          str([r["path"] for r in scanned["files"]]))
    run("select_units.py", "--index", index_path, "--out", out)
    kept = [l.strip() for l in open(out, encoding="utf-8") if l.strip()]
    check("a module that defines nothing is not selected",
          not [p for p in kept if p.endswith("__init__.py")], str(kept))

    # A test file is evidence the code works, not part of the system a reader is being
    # introduced to. Documenting it spends the budget on scaffolding and puts the test
    # beside the thing it tests in the module reference.
    os.makedirs(os.path.join(root, "tests"), exist_ok=True)
    with open(os.path.join(root, "tests", "test_transform.py"), "w",
              encoding="utf-8") as fh:
        fh.write("def test_normalise():\n    assert True\n")
    run("scan_repo.py", "--root", root, "--out", index_path, "--detail")
    with open(index_path, encoding="utf-8") as fh:
        scanned = json.load(fh)
    check("the scanner marks the test file as one",
          any(r.get("is_test") and r.get("symbols") for r in scanned["files"]),
          str([(r["path"], r.get("is_test")) for r in scanned["files"]]))
    run("select_units.py", "--index", index_path, "--out", out)
    kept = [l.strip() for l in open(out, encoding="utf-8") if l.strip()]
    check("a test module is not selected for documentation",
          not [p for p in kept if "test" in p], str(kept))

    # Dropping test files from the selection but not their edges fixes half of it: the
    # scanner's fan_in still counts them, so a helper imported by twenty tests and one
    # module outranks the entry point and takes the budget with it.
    helper = os.path.join(root, "src", "pipeline", "helper.py")
    with open(helper, "w", encoding="utf-8") as fh:
        fh.write("def helper():\n    return 1\n")
    for number in range(6):
        with open(os.path.join(root, "tests", "test_h%d.py" % number), "w",
                  encoding="utf-8") as fh:
            fh.write("from src.pipeline.helper import helper\n\n\n"
                     "def test_h%d():\n    assert helper()\n" % number)
    run("scan_repo.py", "--root", root, "--out", index_path, "--detail")
    with open(index_path, encoding="utf-8") as fh:
        scanned = json.load(fh)
    check("the scanner's own fan_in counts the test imports",
          (scanned.get("fan_in") or {}).get("src/pipeline/helper.py", 0) >= 6,
          repr(scanned.get("fan_in")))
    code, text = run("select_units.py", "--index", index_path, "--out", out, "--top", "1")
    ranked = [line.split()[-1] for line in text.splitlines()
              if line[:1].isdigit() and "fan_in" in line]
    check("but a module only tests import does not win the fan-in budget",
          "src/pipeline/helper.py" not in ranked, text)

    # Every entry point is added whatever the cutoff, which is right with two or three
    # ways in and wrong in a tree of standalone scripts. There the number that decides
    # the cost of the run is not the one that was typed, and it has to say so.
    code, text = run("select_units.py", "--index", index_path, "--out", out, "--top", "1")
    kept = [l.strip() for l in open(out, encoding="utf-8") if l.strip()]
    over = len(kept) > 2
    check("a selection far over the cutoff says so",
          ("WARN" in text and "--top 1" in text) if over else True, text)
    check("and a selection within it stays quiet",
          "was asked for and" not in run("select_units.py", "--index", index_path,
                                         "--out", out, "--top", "25")[1], text)

    # Same index, same selection -- including the order, which units.txt is a contract for.
    run("select_units.py", "--index", index_path, "--out", out)
    first = open(out, encoding="utf-8").read()
    run("select_units.py", "--index", index_path, "--out", out)
    check("select_units is deterministic", first == open(out, encoding="utf-8").read())

    # Ties used to fall out of dict order. Two modules with the same fan-in must select in
    # path order, or the cutoff moves between runs of the same scan.
    with open(index_path, encoding="utf-8") as fh:
        index = json.load(fh)
    tied = dict(index)
    tied["fan_in"] = {r["path"]: 1 for r in index["files"]}
    tied_path = os.path.join(tmp, "tied.json")
    write(tied_path, json.dumps(tied))
    code, _ = run("select_units.py", "--index", tied_path, "--out", out, "--top", "2")
    kept = [l.strip() for l in open(out, encoding="utf-8") if l.strip()]
    check("ties break by path", code == 0 and kept[:2] == sorted(kept[:2]), str(kept))

    # A repository of standalone programs ranks nothing. Built as a real tree and
    # scanned, not by editing an index: the scanner writes `fan_in` by counting incoming
    # edges, so it is *empty* here rather than full of zeroes, and a synthesised map made
    # this pass while the real case selected nothing at all.
    independent = os.path.join(tmp, "independent")
    os.makedirs(independent, exist_ok=True)
    for name in ("tool_a.py", "tool_b.py", "tool_c.py"):
        write(os.path.join(independent, name), "def go():\n    return 1\n")
    flat_index = os.path.join(tmp, "independent.json")
    run("scan_repo.py", "--root", independent, "--out", flat_index, "--detail")
    check("the scanner really does leave fan_in empty here",
          json.load(open(flat_index, encoding="utf-8"))["fan_in"] == {})
    code, text = run("select_units.py", "--index", flat_index, "--out", out)
    kept = [l.strip() for l in open(out, encoding="utf-8") if l.strip()]
    check("a repository with no internal imports still selects its modules",
          code == 0 and len(kept) == 3, "%d: %s" % (code, text[-200:]))
    check("and is warned that the ranking means nothing",
          "carries no information" in text, text)

    code, text = run("select_units.py", "--index", os.path.join(tmp, "nope.json"),
                     "--out", out)
    check("a missing index is an input error", code == 2, text)
    bad = os.path.join(tmp, "bad.json")
    write(bad, json.dumps({"schema_version": 99, "files": []}))
    code, text = run("select_units.py", "--index", bad, "--out", out)
    check("an unsupported schema is an input error", code == 2, text)
    return index_path, root


def driver_tests(tmp, root):
    """pipeline.py: what each component runs, what it skips, and what it will not swallow."""
    build = os.path.join(tmp, "build")

    code, text = run("pipeline.py", "survey", "--root", root, "--build", build,
                     "--dry-run")
    check("survey dry-run runs nothing and exits 0", code == 0, text)
    check("survey names its stages in order",
          text.index("scan_repo") < text.index("validate_index")
          < text.index("select_units"), text)
    check("a stage is named by its component",
          "survey/scan_repo" in text, text[:400])
    check("dry-run writes no index",
          not os.path.exists(os.path.join(build, "structure.json")))

    code, text = run("pipeline.py", "survey", "--root", root, "--build", build,
                     "--policy", "disabled", "--dry-run")
    check("--policy disabled drops the annotation stage",
          "annotate_import_usage" not in text, text)

    code, text = run("pipeline.py", "survey", "--root", root, "--build", build)
    check("survey runs", code == 0, text[-400:])
    check("survey writes the index and the scope",
          os.path.exists(os.path.join(build, "structure.json"))
          and os.path.exists(os.path.join(build, "units.txt")))
    timing_path = os.path.join(build, "timings.jsonl")
    timings = [json.loads(line) for line in open(timing_path, encoding="utf-8")]
    check("the driver records stage and component durations",
          any(r.get("record_type") == "stage" and r.get("stage") == "survey/scan_repo"
              and r.get("duration_seconds", -1) >= 0 for r in timings)
          and any(r.get("record_type") == "component" and r.get("component") == "survey"
                  for r in timings), repr(timings[-3:]))

    code, text = run("pipeline.py", "measure", "--root", root, "--build", build,
                     "--step", "source_reading", "--state", "start")
    check("a model-driven step can start explicit timing", code == 0, text)
    code, text = run("pipeline.py", "measure", "--root", root, "--build", build,
                     "--step", "source_reading", "--state", "stop")
    timings = [json.loads(line) for line in open(timing_path, encoding="utf-8")]
    check("and stopping it writes a model_step duration",
          code == 0 and any(r.get("record_type") == "model_step"
                            and r.get("step") == "source_reading"
                            and r.get("duration_seconds", -1) >= 0 for r in timings), text)

    # The scope checkpoint. Every other invariant in this pipeline is a script that
    # refuses; this one was a paragraph in SKILL.md, so a run that read the units and
    # kept going saw no error at all and carried a wrong scope through every check
    # downstream -- checks compare claims against evidence, never against whether the
    # right modules were chosen.
    check("survey opens the scope checkpoint",
          os.path.isfile(os.path.join(build, "checkpoints", "P1.json")),
          str(os.listdir(build)))
    code, text = run("pipeline.py", "analyze", "--root", root, "--build", build)
    check("analyze refuses while the scope checkpoint is open", code == 1, text[-300:])
    check("and the refusal says what to ask and how to record the answer",
          "is this the right scope" in text and "decide --checkpoint P1" in text, text)

    code, text = run("pipeline.py", "decide", "--checkpoint", "P1", "--build", build,
                     "--note", "top 25 plus the entry points, agreed as the scope")
    check("a decision is recorded", code == 0, text)
    code, text = run("pipeline.py", "decide", "--checkpoint", "P1", "--build", build)
    check("and a decision with no note is refused, since the report would carry nothing",
          code == 2, text)

    # A decision recorded before the question is asked is not one anybody answered, and
    # it is the shape a script written against the unguarded version takes: decide P2
    # straight after survey, and analyze then leaves the standing decision alone because
    # it carries the current index_hash, so check runs with the roles unreviewed.
    code, text = run("pipeline.py", "decide", "--checkpoint", "P2", "--build", build,
                     "--note", "pre-approved before analyze ever ran")
    check("a checkpoint that was never opened cannot be decided", code == 1, text)
    check("and the refusal names the component that opens it", "analyze opens it" in text,
          text)

    # --dry-run says it runs nothing. Recording an approval is the one thing it must not
    # do quietly, since that alone unblocks the next component.
    reopened = os.path.join(build, "checkpoints", "P1.json")
    with open(reopened, encoding="utf-8") as fh:
        kept = json.load(fh)
    with open(reopened, "w", encoding="utf-8") as fh:
        json.dump(dict(kept, state="pending"), fh)
    code, text = run("pipeline.py", "decide", "--checkpoint", "P1", "--build", build,
                     "--note", "previewing only, nothing decided here", "--dry-run")
    with open(reopened, encoding="utf-8") as fh:
        after = json.load(fh)
    check("--dry-run records no decision", code == 0 and after["state"] == "pending",
          repr(after))

    # An open checkpoint blocks everything downstream, not only the next component. A
    # build directory holding an earlier run's artifacts is where it matters: blocking
    # only analyze would leave document and publish free to produce a finished report
    # while the scope decision is still outstanding.
    for later in ("check", "document", "publish"):
        code, text = run("pipeline.py", later, "--root", root, "--build", build)
        check("%s is held by the open scope checkpoint too" % later,
              code == 1 and "held at checkpoint P1" in text, text[-200:])
    with open(reopened, "w", encoding="utf-8") as fh:
        json.dump(kept, fh)

    # analyze puts a packet on disk per unit, so the reading that follows can be fanned
    # out without every task re-running the query.
    code, text = run("pipeline.py", "analyze", "--root", root, "--build", build)
    check("analyze runs", code == 0, text[-400:])
    units = [l.strip() for l in
             open(os.path.join(build, "units.txt"), encoding="utf-8") if l.strip()]
    packets = os.listdir(os.path.join(build, "packets"))
    check("analyze writes one packet per unit", len(packets) == len(units),
          "%d packet(s) for %d unit(s)" % (len(packets), len(units)))
    packet = json.load(open(os.path.join(build, "packets", sorted(packets)[0]),
                            encoding="utf-8"))
    check("a captured packet is the packet, not a log", "context_manifest" in packet,
          str(sorted(packet))[:200])
    check("analyze derives the structural claims",
          os.path.exists(os.path.join(build, "claims.jsonl")))

    # Two distinct module paths must not flatten to one packet name, or the second
    # overwrites the first while the component reports success.
    import hashlib
    seen = {}
    for path in ("a/b__c.py", "a__b/c.py", "a/b/c.py"):
        flat = path.replace("/", "__")
        seen.setdefault("%s.%s.json"
                        % (flat, hashlib.sha256(path.encode()).hexdigest()[:8]),
                        []).append(path)
    check("distinct unit paths get distinct packet names",
          all(len(v) == 1 for v in seen.values()), str(seen))

    # A packet left by a wider earlier scope is a module the reader would analyse and
    # `assemble` would then reject as out of scope, after the budget was spent.
    stale = os.path.join(build, "packets", "gone__module.py.deadbeef.json")
    write(stale, "{}")
    code, text = run("pipeline.py", "analyze", "--root", root, "--build", build, "--force")
    check("analyze clears packets from an earlier scope",
          code == 0 and not os.path.exists(stale), text[-200:])
    check("and still writes the current ones",
          len(os.listdir(os.path.join(build, "packets"))) == len(units))

    # A stage that fails must stop its component, and its exit code must arrive unchanged.
    #
    # The inputs are present and one of them is corrupt, which is what makes this a stage
    # failure. An empty build directory was the fixture here until the preflight told a
    # skipped step apart from a broken one: `check` on a build with no survey in it now
    # names the survey and exits 2 before any stage runs, so it no longer produces the
    # failing stage this is about.
    broken = os.path.join(tmp, "broken")
    os.makedirs(broken, exist_ok=True)
    write(os.path.join(broken, "structure.json"), "{ this is not json")
    write(os.path.join(broken, "claims.jsonl"), "")
    code, text = run("pipeline.py", "check", "--root", root, "--build", broken)
    check("a failing stage stops the component", code != 0, text[-300:])
    check("the failing stage is named", "check/assemble" in text, text[-300:])
    check("a stage that never ran is reported as such",
          "did not run" in text or "last stage" in text, text[-300:])

    # The other half of the same distinction, and the reason the preflight exists: an agent
    # resuming with no memory of this run gets the step it skipped, not a traceback from a
    # script that was handed a path to a file nobody wrote.
    empty = os.path.join(tmp, "no-survey")
    os.makedirs(empty, exist_ok=True)
    code, text = run("pipeline.py", "document", "--root", root, "--build", empty,
                     "--docs", os.path.join(tmp, "docs"))
    check("a component with no predecessor is an input error", code == 2, text[-400:])
    check("it names the step that did not run", "which survey produces" in text,
          text[-400:])
    check("it names the command that produces it", "pipeline.py survey --root" in text,
          text[-400:])
    check("it offers status, which answers for the whole run", "status --root" in text,
          text[-400:])
    check("no traceback reaches the reader", "Traceback" not in text, text[-400:])
    check("and nothing ran", not os.path.exists(os.path.join(empty, "doc.json")))

    # The optional analyses are absent far more often than they are broken.
    code, text = run("pipeline.py", "document", "--root", root, "--build", build,
                     "--docs", os.path.join(tmp, "docs"), "--preset", "outside-in",
                     "--dry-run")
    check("document skips analyses that were not written",
          text.count("-- skip ") == 5, text)
    check("document says why it skipped each one", "will say so" in text, text)

    # No outline is mandatory, and none is silently imposed: with nothing chosen, document
    # builds the survey's recommendation and says it is provisional.
    code, text = run("pipeline.py", "document", "--root", root, "--build", build,
                     "--docs", os.path.join(tmp, "docs"), "--dry-run")
    check("document without a choice builds a recommendation labelled provisional",
          code == 0 and "PROVISIONAL" in text and "template --use" in text, text[:600])
    check("a dry run records no choice",
          not os.path.exists(os.path.join(build, "template.json")), text[:300])

    # Listing the choices writes nothing, and recording one needs a reason.
    code, text = run("pipeline.py", "template", "--root", root, "--build", build)
    check("template lists presets, the manual template and external files",
          code == 0 and "architecture" in text and "manual" in text and "<path>" in text,
          text[:400])
    code, text = run("pipeline.py", "template", "--root", root, "--build", build,
                     "--use", "manual", "--note", "ok")
    check("a template choice without a reason is refused",
          code == 2 and not os.path.exists(os.path.join(build, "template.json")), text[-300:])

    code, text = run("pipeline.py", "template", "--root", root, "--build", build,
                     "--use", "manual", "--drop", "appendix/",
                     "--note", "user picked the manual without its appendix pages")
    check("the manual template can be recorded as a selection", code == 0, text[-300:])
    code, text = run("pipeline.py", "document", "--root", root, "--build", build,
                     "--docs", os.path.join(tmp, "docs"), "--dry-run")
    check("document builds the recorded manual template",
          "preset: manual (template manual" in text, text[:300])
    check("a first run says the draft would be written and writes nothing",
          "would write" in text
          and not os.path.exists(os.path.join(build, "manual-analysis.json")), text[:400])
    check("the chosen template reaches the model build",
          "--template %s" % os.path.join(build, "template.json") in text, text[-600:])
    write(os.path.join(build, "architecture-analysis.json"), "{}")
    code, text = run("pipeline.py", "document", "--root", root, "--build", build,
                     "--docs", os.path.join(tmp, "docs"), "--dry-run")
    # An analysis appearing on disk does not change the deliverable under the reader's
    # feet. It is material the chosen template may use, not a vote for a different one.
    check("an analysis on disk does not change the recorded choice",
          "preset: manual (template manual" in text, text[:300])

    # A preset is a choice like any other, and an external outline is one too.
    code, text = run("pipeline.py", "template", "--root", root, "--build", build,
                     "--use", "onboarding",
                     "--note", "user wants the file-by-file onboarding tour")
    code, text = run("pipeline.py", "document", "--root", root, "--build", build,
                     "--docs", os.path.join(tmp, "docs"), "--dry-run")
    check("a recorded preset is what document builds",
          "preset: onboarding" in text and "--template" not in text, text[:300])
    outline = os.path.join(tmp, "outline.md")
    write(outline, "# Manual\n\n## Install\n- What must be installed?\n\n"
                   "## Configure\nEvery setting and its default.\n")
    code, text = run("pipeline.py", "template", "--root", root, "--build", build,
                     "--use", outline, "--note", "user supplied their own two-page outline")
    check("an external outline can be recorded", code == 0, text[-300:])
    code, text = run("pipeline.py", "document", "--root", root, "--build", build,
                     "--docs", os.path.join(tmp, "docs"), "--dry-run")
    check("document builds against the external outline",
          "preset: manual (template outline" in text, text[:300])

    # Checking a written tree needs no run, and judges it by the recorded outline unless
    # another template is named explicitly.
    written = os.path.join(tmp, "written-docs")
    os.makedirs(written, exist_ok=True)
    write(os.path.join(written, "install.md"),
          "# Install\n\n%s\n" % " ".join(["Run make install from the checkout."] * 5))
    code, text = run("pipeline.py", "template", "--root", root, "--build", build,
                     "--check-docs", written)
    check("check-docs reports the recorded outline's missing page",
          code == 1 and "present    install" in text and "missing    configure" in text,
          text[-400:])
    code, text = run("pipeline.py", "template", "--root", root, "--build", build,
                     "--check-docs", written, "--use", "manual",
                     "--sections", "getting_started/introduction")
    check("an explicit template wins over the recorded one",
          code == 1 and "getting_started/introduction" in text and "install " not in text,
          text[-400:])
    os.remove(os.path.join(build, "template.json"))
    code, text = run("pipeline.py", "document", "--root", root, "--build", build,
                     "--docs", os.path.join(tmp, "docs"), "--preset", "outside-in",
                     "--dry-run")
    check("an existing analysis reaches the model build",
          "--architecture" in text, text)
    code, text = run("pipeline.py", "document", "--root", root, "--build", build,
                     "--docs", os.path.join(tmp, "docs"), "--preset", "architecture",
                     "--dry-run")
    check("--preset overrides the choice", "preset: architecture" in text, text[:200])
    # The three analyses are independently optional, and `outside-in` renders whichever
    # of them exists: an operations analysis alone must still reach the model build.
    os.remove(os.path.join(build, "architecture-analysis.json"))
    write(os.path.join(build, "operations-analysis.json"), "{}")
    code, text = run("pipeline.py", "document", "--root", root, "--build", build,
                     "--docs", os.path.join(tmp, "docs"), "--preset", "outside-in",
                     "--dry-run")
    check("an operations analysis alone reaches the model build",
          "--operations" in text, text)
    os.remove(os.path.join(build, "operations-analysis.json"))
    write(os.path.join(build, "architecture-analysis.json"), "{}")
    code, text = run("pipeline.py", "review", "--root", root, "--build", build,
                     "--docs", os.path.join(tmp, "docs"), "--dry-run")
    check("review passes the analyses to the prose check and the gate",
          text.count("--architecture") == 2, text)
    os.remove(os.path.join(build, "architecture-analysis.json"))

    # Hand-written claims are the one thing in the build directory no script can rebuild.
    claims = os.path.join(build, "claims.jsonl")
    with open(claims, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"id": "claim:a-calls-b", "kind": "calls"}) + "\n")
    code, text = run("pipeline.py", "analyze", "--root", root, "--build", build)
    check("analyze refuses to overwrite hand-written claims", code == 1, text[-300:])
    check("the refusal names them", "claim:a-calls-b" in text, text[-300:])
    check("the refusal did not re-derive first",
          "claim:a-calls-b" in open(claims, encoding="utf-8").read())
    code, text = run("pipeline.py", "analyze", "--root", root, "--build", build, "--force")
    check("--force gets past the refusal", code == 0, text[-300:])
    check("survey is not held back by hand-written claims",
          run("pipeline.py", "survey", "--root", root, "--build", build,
              "--dry-run")[0] == 0)

    code, text = run("pipeline.py", "survey", "--root", os.path.join(tmp, "no-such-dir"),
                     "--build", build)
    check("a missing root is an input error", code == 2, text)
    code, text = run("pipeline.py", "review", "--root", root, "--build", build,
                     "--review", os.path.join(tmp, "no-such-review.jsonl"))
    check("a missing review file is an input error", code == 2, text)
    code, text = run("pipeline.py", "audit", "--root", root, "--build", build)
    check("a component this driver does not have is refused", code != 0, text[-200:])

    # check_prose stores these counts under coverage. P4 used to read top-level keys,
    # so it never opened even when every manual section was waiting for review.
    report_dir = os.path.join(tmp, "p4-report")
    os.makedirs(report_dir)
    write(os.path.join(report_dir, "prose-report.json"), json.dumps({
        "status": "review_required",
        "coverage": {"queued": 19, "reviewed": 0},
    }))
    check("P4 detects the review queue written by check_prose",
          pipeline.prose_queued(report_dir))
    write(os.path.join(report_dir, "prose-report.json"), json.dumps({
        "status": "passed",
        "coverage": {"queued": 19, "reviewed": 19},
    }))
    check("P4 stays closed after the whole queue is reviewed",
          not pipeline.prose_queued(report_dir))


def diagram_directory_test(tmp):
    """Both diagram families share a directory; neither may report the other as unclaimed."""
    root = os.path.join(tmp, "flow-repo")
    shutil.copytree(FIXTURE, root)
    build = os.path.join(root, ".docs-build")
    diagrams = os.path.join(root, "docs", "_diagrams")
    code, text = run("pipeline.py", "survey", "--root", ".", cwd=root)
    if code != 0:
        check("end-to-end survey", False, text[-300:])
        return

    index = json.load(open(os.path.join(build, "structure.json"), encoding="utf-8"))
    index_hash = index["index_hash"]
    with open(os.path.join(build, "claims.jsonl"), "a", encoding="utf-8") as fh:
        for row in (("claim:entry-calls-normalise", "src/pipeline/entry.py", "main",
                     "src/pipeline/transform.py", "normalise", 7),
                    ("claim:normalise-calls-save", "src/pipeline/transform.py",
                     "normalise", "src/pipeline/store.py", "save", 7)):
            cid, src, sym, dst, target, line = row
            fh.write(json.dumps({
                "id": cid, "kind": "calls", "subject": "symbol:%s:%s" % (src, sym),
                "object": "symbol:%s:%s" % (dst, target),
                "evidence": [{"path": src, "line_start": line, "line_end": line}],
                "index_hash": index_hash}, sort_keys=True) + "\n")
    write(os.path.join(build, "flow-analysis.json"), json.dumps({
        "flow_version": 1, "index_hash": index_hash, "flows": [{
            "id": "flow:save", "name": "Saving a value", "status": "observed",
            "trigger": {"kind": "cli", "text": "The console script runs main.",
                        "status": "declared",
                        "evidence": [{"path": "pyproject.toml", "line_start": 7}]},
            "steps": [
                {"id": "step:1", "from": "symbol:src/pipeline/entry.py:main",
                 "to": "symbol:src/pipeline/transform.py:normalise",
                 "text": "The entry point hands its argument to normalise.",
                 "status": "observed", "claim_ids": ["claim:entry-calls-normalise"],
                 "evidence": [{"path": "src/pipeline/entry.py", "line_start": 7}]},
                {"id": "step:2", "from": "symbol:src/pipeline/transform.py:normalise",
                 "to": "symbol:src/pipeline/store.py:save",
                 "text": "normalise trims the value and passes it on.",
                 "status": "observed", "claim_ids": ["claim:normalise-calls-save"],
                 "evidence": [{"path": "src/pipeline/transform.py", "line_start": 7}]}],
            "outcome": {"status": "observed", "text": "save returns a length.",
                        "evidence": [{"path": "src/pipeline/store.py",
                                      "line_start": 5}]}}]}))

    code, text = run("verify_doc.py", "--claims", os.path.join(build, "claims.jsonl"),
                     "--fragments", os.path.join(build, "claims.jsonl"),
                     "--index", os.path.join(build, "structure.json"),
                     "--root", root, "--out-dir", build)
    code, text = run("validate_flows.py", os.path.join(build, "flow-analysis.json"),
                     "--index", os.path.join(build, "structure.json"),
                     "--claims", os.path.join(build, "claims.verified.jsonl"),
                     "--out", os.path.join(build, "flow-report.json"))
    check("the fixture's flow validates", code == 0, text[-300:])

    graph = os.path.join(build, "class-graph.json")
    run("build_class_graph.py", "--index", os.path.join(build, "structure.json"),
        "--claims", os.path.join(build, "claims.verified.jsonl"), "--out", graph)
    run("build_diagrams.py", "--class-graph", graph, "--out", diagrams)
    run("build_flow_diagrams.py", "--flows", os.path.join(build, "flow-analysis.json"),
        "--report", os.path.join(build, "flow-report.json"), "--out", diagrams)
    code, text = run("validate_flow_diagrams.py", diagrams,
                     "--flows", os.path.join(build, "flow-analysis.json"))
    check("a class view beside a sequence view is not reported as unclaimed",
          code == 0 and "full-repository.puml" not in text, text[-400:])

    # The check still has teeth: a .puml no manifest names is exactly what it is for.
    write(os.path.join(diagrams, "stray.puml"), "@startuml\n@enduml\n")
    code, text = run("validate_flow_diagrams.py", diagrams,
                     "--flows", os.path.join(build, "flow-analysis.json"))
    check("a .puml no manifest names is still reported",
          code == 1 and "stray.puml" in text, text[-300:])


def revision_tests(tmp):
    """render mints immutable draft revisions, prunes them, and never reuses a number."""
    from draft_artifact import tree_hash, verify_revision
    root = os.path.join(tmp, "rev-repo")
    build = os.path.join(root, ".docs-build")
    docs = os.path.join(root, "docs")
    drafts = os.path.join(build, "drafts")
    os.makedirs(os.path.join(build, "diagrams"))
    os.makedirs(docs)

    def model(text):
        write(os.path.join(build, "doc.json"), json.dumps({
            "format_version": 2, "preset": "onboarding", "claims": [], "statements": [],
            "authored_pages": [],
            "pages": [{"id": "overview", "title": "Overview", "order": 0,
                       "mandatory": True, "covers": [],
                       "blocks": [{"id": "block:a", "type": "prose", "manual_block": True,
                                   "text": text, "claim_refs": [], "analysis_refs": []}]}]}))

    def render(*extra):
        return run("pipeline.py", "render", "--root", root, "--build", build,
                   "--docs", docs, *extra)

    def manifest():
        with open(os.path.join(build, "render-manifest.json"), encoding="utf-8") as fh:
            return json.load(fh)

    def revisions():
        return sorted(n for n in os.listdir(drafts)
                      if n.startswith("rev-") and not n.endswith(".meta"))

    model("Read the configuration before starting.")
    code, text = render()
    check("render mints rev-0001", code == 0 and revisions() == ["rev-0001"], text[-300:])
    check("the manifest names the revision and is version 2",
          manifest().get("revision") == "rev-0001"
          and manifest().get("render_manifest_version") == 2, repr(manifest()))
    first_hash = tree_hash(os.path.join(drafts, "rev-0001"))
    record_path = os.path.join(drafts, "rev-0001.meta", "revision.json")
    with open(record_path, encoding="utf-8") as fh:
        record = json.load(fh)
    check("revision.json sits beside the snapshot and records its hash",
          record["revision_version"] == 1 and record["draft_hash"] == first_hash
          and record["previous"] is None, repr(record))
    check("nothing but the rendered tree is inside the snapshot",
          not os.path.exists(os.path.join(drafts, "rev-0001", "revision.json")))

    code, text = render()
    check("rendering the same model again mints nothing",
          code == 0 and revisions() == ["rev-0001"] and manifest()["revision"] == "rev-0001",
          text[-300:])

    model("Read the configuration, then start the service.")
    code, text = render()
    check("a changed block mints rev-0002",
          code == 0 and revisions() == ["rev-0001", "rev-0002"]
          and manifest()["revision"] == "rev-0002", text[-300:])
    check("and leaves rev-0001 byte-for-byte as it was",
          tree_hash(os.path.join(drafts, "rev-0001")) == first_hash
          and verify_revision(drafts, "rev-0001") is None)

    code, text = render("--keep-revisions", "2")
    check("--keep-revisions below 3 is refused", code != 0 and "at least 3" in text, text[-200:])

    # Seal rev-0002, then render until it would be pruned: the seal protects it.
    write(os.path.join(build, "publish-seal.json"),
          json.dumps({"seal_version": 2, "revision": "rev-0002"}))
    for n in (3, 4, 5):
        model("Distinct draft number %d." % n)
        code, text = render("--keep-revisions", "3")
        check("distinct render %d succeeds" % n, code == 0, text[-300:])
    check("with --keep-revisions 3 the latest three survive, and the sealed rev-0002 too",
          revisions() == ["rev-0002", "rev-0003", "rev-0004", "rev-0005"], repr(revisions()))
    check("pruning removes the metadata beside the snapshot too",
          not os.path.exists(os.path.join(drafts, "rev-0001.meta")))
    os.remove(os.path.join(build, "publish-seal.json"))
    model("Distinct draft number 6.")
    code, text = render("--keep-revisions", "3")
    check("an unsealed old revision is pruned and the cap holds",
          revisions() == ["rev-0004", "rev-0005", "rev-0006"] and "pruned rev-0002" in text,
          repr(revisions()))
    model("Distinct draft number 7.")
    render("--keep-revisions", "3")
    check("numbers are never reused after pruning",
          revisions() == ["rev-0005", "rev-0006", "rev-0007"], repr(revisions()))
    with open(os.path.join(drafts, "counter.json"), encoding="utf-8") as fh:
        check("the counter records the highest number ever used",
              json.load(fh) == {"highest": 7})

    # --- The P4 identity ignores the revision label.
    def queue_hash(label):
        write(os.path.join(build, "prose-report.json"), json.dumps({"review_queue": [
            {"block": "block:a", "target_id": "block:a", "content_hash": "sha256:1",
             "draft_revision": label}]}))
        return pipeline.review_queue_hash(build)

    check("review_queue_hash is the same for queues that differ only in draft_revision",
          queue_hash("rev-0001") == queue_hash("rev-0002") and queue_hash("rev-0001"))
    write(os.path.join(build, "prose-report.json"), json.dumps({"review_queue": [
        {"block": "block:a", "target_id": "block:a", "content_hash": "sha256:2",
         "draft_revision": "rev-0001"}]}))
    check("but a changed reading still changes it",
          pipeline.review_queue_hash(build) != queue_hash("rev-0001"))

    # --- Review history is kept per revision, and never overwritten.
    revision = manifest()["revision"]
    meta = os.path.join(drafts, revision + ".meta")
    review_file = os.path.join(build, "prose-review.jsonl")
    args = type("Args", (), {"build": build, "review": review_file})()
    for round_number in (1, 2):
        write(review_file, '{"round": %d}\n' % round_number)
        before = pipeline.file_stamp(os.path.join(build, "prose-report.json"))
        write(os.path.join(build, "prose-report.json"),
              json.dumps({"review_queue": [], "round": round_number}))
        pipeline.record_review_history(args, before)
    check("two review rounds leave numbered history beside the revision",
          sorted(n for n in os.listdir(meta) if n != "revision.json")
          == ["prose-report-01.json", "prose-report-02.json",
              "review-01.jsonl", "review-02.jsonl"], repr(os.listdir(meta)))
    with open(os.path.join(meta, "review-01.jsonl"), encoding="utf-8") as fh:
        check("the first round survives the second", fh.read() == '{"round": 1}\n')
    with open(os.path.join(meta, "revision.json"), encoding="utf-8") as fh:
        recorded = json.load(fh)["draft_hash"]
    check("and nothing is written inside the snapshot",
          tree_hash(os.path.join(drafts, revision)) == recorded)
    check("a review that did not rewrite the prose report records no round",
          pipeline.record_review_history(
              args, pipeline.file_stamp(os.path.join(build, "prose-report.json"))) is None
          and len(os.listdir(meta)) == 5)

    code, text = run("pipeline.py", "render", "--root", root, "--build", build,
                     "--docs", docs, "--dry-run")
    check("render --dry-run names the new stage",
          code == 0 and "render/snapshot_revision" in text, text[-300:])


def resume_tests(tmp):
    """`resume` reports the draft-review loop and never writes or blocks anything."""
    from draft_artifact import tree_hash
    created = "2026-01-01T00:00:00Z"

    def loop(name, scan=True):
        root = os.path.join(tmp, name)
        build = os.path.join(root, ".docs-build")
        os.makedirs(build)
        if scan:
            write(os.path.join(build, "structure.json"),
                  json.dumps({"index_hash": "sha256:s"}))
        return root, build

    def mint(build, number, rounds=(), previous=None, stage=False, report=None):
        """Fabricate rev-NNNN and its review rounds; each round is a list of findings."""
        drafts, name = os.path.join(build, "drafts"), "rev-%04d" % number
        snapshot = os.path.join(drafts, name)
        os.makedirs(snapshot)
        write(os.path.join(snapshot, "index.rst"), "Draft %d\n" % number)
        meta = os.path.join(drafts, name + ".meta")
        os.makedirs(meta)
        write(os.path.join(meta, "revision.json"), json.dumps({
            "revision_version": 1, "revision": name, "created_at": created,
            "draft_hash": tree_hash(snapshot), "previous": previous}))
        for index, findings in enumerate(rounds, 1):
            write(os.path.join(meta, "review-%02d.jsonl" % index), json.dumps(
                {"review_version": 2, "findings": [
                    {"finding_id": fid, "severity": sev, "location": "page:%s" % fid,
                     "why": "w", "requested": "fix %s" % fid, "state": state}
                    for fid, sev, state in findings]}) + "\n")
            write(os.path.join(meta, "prose-report-%02d.json" % index), json.dumps(
                report or {"coverage": {"queued": 2}, "unreviewed": ["block:u"],
                           "stale_reviews": ["block:s"]}))
        if stage:
            shutil.rmtree(os.path.join(build, "rendered-docs"), ignore_errors=True)
            shutil.copytree(snapshot, os.path.join(build, "rendered-docs"))
        return name

    def resume(root, build):
        return run("pipeline.py", "resume", "--root", root, "--build", build)

    def next_line(text):
        return [l for l in text.splitlines() if l.startswith("next")][-1]

    def snapshot_of(build):
        held = {}
        for directory, _dirs, files in os.walk(build):
            for name in files:
                path = os.path.join(directory, name)
                with open(path, "rb") as fh:
                    held[path] = (fh.read(), os.stat(path).st_mtime_ns)
        return held

    # --- No scan: says so, creates nothing.
    root = os.path.join(tmp, "resume-none")
    os.makedirs(root)
    code, text = resume(root, os.path.join(root, ".docs-build"))
    check("resume with no build exits 0 and says there is no scan",
          code == 0 and "no scan yet" in text, text)
    check("and creates no directory", os.listdir(root) == [])

    # --- Built before revision snapshots.
    root, build = loop("resume-old")
    write(os.path.join(build, "continuation.md"), "Old note body.\n")
    code, text = resume(root, build)
    check("a build with no drafts/ predates revision snapshots",
          code == 0 and "predates revision snapshots; run render" in text
          and "Old note body." in text, text)

    # --- The full picture, and read-only.
    root, build = loop("resume-full")
    mint(build, 1, rounds=[[("F1", "blocking", "open"), ("F2", "blocking", "open")]])
    mint(build, 2, previous="rev-0001", stage=True,
         rounds=[[("F1", "blocking", "open"), ("F2", "blocking", "resolved"),
                  ("F3", "minor", "open")]])
    write(os.path.join(build, "publish-seal.json"),
          json.dumps({"seal_version": 2, "revision": "rev-0001"}))
    write(os.path.join(build, "continuation.md"), "Budget: 3 of 5 rounds used.\n")
    before = snapshot_of(build)
    code, text = resume(root, build)
    check("resume exits 0 on a build with revisions, reviews, a seal and a note",
          code == 0, text)
    check("resume changes no file and appends no timing",
          before == snapshot_of(build)
          and not os.path.exists(os.path.join(build, "timings.jsonl")))
    check("the sealed revision is named and marked not the latest",
          "rev-0001 (not the latest: latest is rev-0002)" in text, text)
    check("review state counts queued, unreviewed and stale blocks",
          "2 block(s) queued, 1 unreviewed, 1 stale" in text
          and "stale: block:s" in text, text)
    check("a blocking finding raised on rev-0001 and still open says since rev-0001",
          "[blocking] F1" in text and "since rev-0001" in text, text)
    check("a finding resolved on rev-0002 is not listed",
          "F2" not in text.split("open findings")[1].split("continuation")[0], text)
    check("the note prints under the not-checked heading, with no age warning when fresh",
          "continuation note (written by the previous session, not checked)" in text
          and "Budget: 3 of 5 rounds used." in text and "older than" not in text, text)
    check("open blocking findings route before render",
          "route the open findings" in next_line(text), next_line(text))
    code, text = run("pipeline.py", "status", "--root", root, "--build", build)
    check("status points at resume when drafts exist",
          "drafts     rev-0002 latest; 1 open blocking finding(s) -- `resume` for the "
          "loop" in text, text)
    root_s, build_s = loop("resume-nodrafts")
    code, text = run("pipeline.py", "status", "--root", root_s, "--build", build_s)
    check("status prints no drafts line otherwise",
          code == 0 and "drafts " not in text, text)

    # --- A note older than the latest revision is flagged.
    os.utime(os.path.join(build, "continuation.md"), (1_500_000_000, 1_500_000_000))
    code, text = resume(root, build)
    check("a note older than the latest revision gets the warning",
          "this note is older than rev-0002" in text, text)

    # --- Next step, one case each.
    root, build = loop("resume-next-render")
    mint(build, 1, stage=True)
    write(os.path.join(build, "rendered-docs", "index.rst"), "edited after render\n")
    code, text = resume(root, build)
    check("staging that differs from the latest revision suggests render",
          code == 0 and "differs from rev-0001" in text and " render " in next_line(text),
          text)
    root, build = loop("resume-next-review")
    mint(build, 1, stage=True)
    code, text = resume(root, build)
    check("a revision with no review round suggests review",
          " review " in next_line(text), text)
    root, build = loop("resume-next-publish")
    mint(build, 1, stage=True, rounds=[[]], report={"coverage": {"queued": 0}})
    write(os.path.join(build, "publish-seal.json"),
          json.dumps({"seal_version": 2, "revision": "rev-0001"}))
    write(os.path.join(build, "generation-report.json"), json.dumps({"status": "passed"}))
    code, text = resume(root, build)
    check("a sealed latest revision with a passed report suggests publish",
          " publish " in next_line(text), text)
    root, build = loop("resume-next-p4")
    mint(build, 1, stage=True, rounds=[[]], report={"coverage": {"queued": 1}})
    write(os.path.join(build, "prose-report.json"),
          json.dumps({"review_queue": [{"block": "block:a"}]}))
    os.makedirs(os.path.join(build, "checkpoints"))
    write(os.path.join(build, "checkpoints", "P4.json"),
          json.dumps({"checkpoint": "P4", "state": "pending", "index_hash": "sha256:s"}))
    code, text = resume(root, build)
    check("an open P4 suggests decide",
          " decide " in next_line(text) and "--checkpoint P4" in next_line(text), text)

    # --- No progress, and the cases that must not print it.
    both = [("F1", "blocking", "open"), ("F2", "blocking", "open")]
    marker = ("no progress: the same 2 blocking finding(s) stayed open across rev-0002 "
              "and rev-0003: F1, F2")
    root, build = loop("resume-stall")
    mint(build, 1, rounds=[both])
    mint(build, 2, previous="rev-0001", rounds=[both])
    mint(build, 3, previous="rev-0002", stage=True, rounds=[both])
    write(os.path.join(build, "doc.json"), json.dumps({
        "format_version": 2, "preset": "onboarding", "claims": [], "statements": [],
        "authored_pages": [],
        "pages": [{"id": "overview", "title": "Overview", "order": 0, "mandatory": True,
                   "covers": [],
                   "blocks": [{"id": "block:a", "type": "prose", "manual_block": True,
                               "text": "Read it.", "claim_refs": [],
                               "analysis_refs": []}]}]}))
    os.makedirs(os.path.join(build, "diagrams"))
    code, text = resume(root, build)
    check("the same blocking ids open across rev-0002 and rev-0003 print no progress",
          code == 0 and marker in text
          and "the stop rule in workflow.md applies; the Coordinator decides whether "
              "to stop" in text, text)
    code, text = run("pipeline.py", "render", "--root", root, "--build", build,
                     "--docs", os.path.join(root, "docs"))
    check("render still runs after a no-progress report",
          code == 0 and os.path.isdir(os.path.join(build, "drafts", "rev-0004")),
          text[-300:])

    root, build = loop("resume-subset")
    mint(build, 1, rounds=[both])
    mint(build, 2, previous="rev-0001", rounds=[[("F1", "blocking", "open")]])
    code, text = resume(root, build)
    check("{F1} against {F1, F2} is progress",
          code == 0 and "no progress" not in text, text)

    root, build = loop("resume-same-revision")
    mint(build, 1, rounds=[both, both])
    code, text = resume(root, build)
    check("two rounds on the same revision are not a stall",
          code == 0 and "no progress" not in text, text)

    root, build = loop("resume-empty")
    mint(build, 1, rounds=[[]])
    mint(build, 2, previous="rev-0001", rounds=[[]])
    code, text = resume(root, build)
    check("empty sets are not a stall", code == 0 and "no progress" not in text, text)

    root, build = loop("resume-pruned")
    mint(build, 3, rounds=[both])
    mint(build, 4, previous="rev-0003", rounds=[both])
    code, text = resume(root, build)
    check("a finding first seen on the oldest kept revision says it may be older",
          "since rev-0003 (or earlier; older revisions were pruned)" in text, text)

    # --- A damaged revision is named, not fatal.
    root, build = loop("resume-damaged")
    mint(build, 1, rounds=[[]])
    mint(build, 2, previous="rev-0001", stage=True, rounds=[[]])
    write(os.path.join(build, "drafts", "rev-0002.meta", "revision.json"), "{not json")
    code, text = resume(root, build)
    check("an unreadable revision.json is named and resume still exits 0",
          code == 0 and "rev-0002: revision.json is missing or unreadable" in text, text)

    # --- Valid JSON of the wrong type is damage, not a crash.
    root, build = loop("resume-wrongtype-report")
    mint(build, 1, stage=True, rounds=[[]])
    write(os.path.join(build, "drafts", "rev-0001.meta", "prose-report-01.json"),
          json.dumps(["damaged report"]))
    code, text = resume(root, build)
    check("a list-valued prose-report-01.json leaves resume at exit 0 with a next step",
          code == 0 and "no readable prose report for rev-0001" in text
          and next_line(text), text)

    root, build = loop("resume-wrongtype-generation")
    mint(build, 1, stage=True, rounds=[[]], report={"coverage": {"queued": 0}})
    write(os.path.join(build, "publish-seal.json"),
          json.dumps({"seal_version": 2, "revision": "rev-0001"}))
    write(os.path.join(build, "generation-report.json"), json.dumps(["damaged report"]))
    code, text = resume(root, build)
    check("a list-valued generation-report.json leaves resume at exit 0 with a next step",
          code == 0 and " review " in next_line(text), text)

    # --- The suggested command carries the options that say where the work is.
    root, build = loop("resume-options")
    mint(build, 1, stage=True, rounds=[[]], report={"coverage": {"queued": 0}})
    write(os.path.join(build, "publish-seal.json"),
          json.dumps({"seal_version": 2, "revision": "rev-0001"}))
    write(os.path.join(build, "generation-report.json"), json.dumps({"status": "passed"}))
    code, text = resume(root, build)
    check("a default run's suggestion carries neither --docs nor --staging",
          " publish " in next_line(text) and "--docs" not in next_line(text)
          and "--staging" not in next_line(text), next_line(text))
    code, text = run("pipeline.py", "resume", "--root", root, "--build", build,
                     "--docs", "site-docs")
    check("--docs site-docs is carried onto the suggested publish",
          " publish " in next_line(text) and "--docs %s" % os.path.join(root, "site-docs")
          in next_line(text), next_line(text))
    root, build = loop("resume-options-review")
    mint(build, 1)
    shutil.copytree(os.path.join(build, "drafts", "rev-0001"),
                    os.path.join(root, "elsewhere"))
    code, text = run("pipeline.py", "resume", "--root", root, "--build", build,
                     "--staging", "elsewhere")
    check("--staging is carried onto the suggested review",
          " review " in next_line(text)
          and "--staging %s" % os.path.join(root, "elsewhere") in next_line(text),
          next_line(text))
    args = pipeline.argparse.Namespace(root=".", build=pipeline.DEFAULT_BUILD, docs="x/docs",
                                       staging=None)
    check("invocation_args carries --docs for render and publish only",
          "--docs x/docs" in pipeline.invocation_args(args, "render")
          and "--docs x/docs" in pipeline.invocation_args(args, "publish")
          and "--docs" not in pipeline.invocation_args(args, "review"))


def main():
    tmp = tempfile.mkdtemp(prefix="pipeline-test-")
    try:
        _index, root = units_tests(tmp)
        driver_tests(tmp, root)
        diagram_directory_test(tmp)
        revision_tests(tmp)
        resume_tests(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if FAILURES:
        print("FAILED %d check(s): %s" % (len(FAILURES), ", ".join(FAILURES)))
        return 1
    print("all pipeline checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
