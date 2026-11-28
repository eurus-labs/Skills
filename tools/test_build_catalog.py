#!/usr/bin/env python3
"""catalog.json must be complete, reproducible, and score only what the eval board trusts.

The extension and a later web page read catalog.json, so a stale file or a score that counts an unfinished run
would mislead every reader. The first classes build a small repository of known scores in a temporary folder;
the last runs `--check` on this repository, so a forgotten rebuild fails here and in CI.

    python3 tools/test_build_catalog.py
"""

import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_catalog as bc  # noqa: E402

FIRES = "---\ntype: tool_used\ntool: Skill\ninput_match: '\"skill\"\\s*:\\s*\"(?:[\\w-]+:)?%s\"'\n---\n"
QUIET = FIRES[:-4] + "min: 0\nmax: 0\n---\n"


def put(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def put_json(path, doc):
    put(path, json.dumps(doc))


def case_doc(name, score, error=None):
    return {"name": name, "aggregates": {"score": score}, "arms": {"with": [{"error": error}]}}


def make_repo(root):
    """Two plugins. alpha has skills one and two and three cases; beta has a skill and no eval case."""
    put_json(os.path.join(root, ".github", "plugin", "marketplace.json"), {
        "name": "eurus-labs", "metadata": {"version": "9.9.9"},
        "plugins": [{"name": "beta", "version": "0.2.0", "description": "Second."},
                    {"name": "alpha", "version": "1.0.0", "description": "First."}]})
    for plugin, skills in (("alpha", ["one", "two"]), ("beta", ["only"])):
        base = os.path.join(root, "plugins", plugin)
        put_json(os.path.join(base, ".github", "plugin", "plugin.json"), {
            "name": plugin, "version": "1.0.0" if plugin == "alpha" else "0.2.0",
            "skills": ["./skills/%s/" % s for s in skills]})
        for skill in skills:
            put(os.path.join(base, "skills", skill, "SKILL.md"),
                "---\nname: %s\ndescription: Does %s.\n---\n" % (skill, skill))
    alpha = os.path.join(root, "plugins", "alpha", "evals")
    for kind, name, skill, quiet in (("trigger", "one-fires", "one", False), ("trigger", "one-quiet", "one", True),
                                     ("behavior", "two-works", "two", False)):
        put(os.path.join(alpha, kind, name, "prompt.md"), "---\ndescription: %s case\n---\n\nDo it.\n" % name)
        put(os.path.join(alpha, kind, name, "graders", "g.md"), (QUIET if quiet else FIRES) % skill)
    return root


def archive(root, stamp, cases, host=None, partial=False, plugin="alpha", folder="archive"):
    doc = {"schemaVersion": 1, "partial": partial, "cases": cases}
    if host:
        doc["host"] = host
    put_json(os.path.join(root, "plugins", plugin, "evals", folder, stamp, "aggregate-result.json"), doc)


def build_repo_with_runs(root):
    make_repo(root)
    archive(root, "2026-01-01T00-00-00Z", [case_doc("one-fires", 1.0), case_doc("one-quiet", 0.5), case_doc("two-works", 0.8)])
    archive(root, "2026-01-02T00-00-00Z", [case_doc("one-fires", 0.6)])
    archive(root, "2026-01-03T00-00-00Z", [case_doc("one-fires", 0.9)], host="copilot")
    archive(root, "2026-01-04T00-00-00Z", [case_doc("one-fires", 0.1)], partial=True)
    return root


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.root = build_repo_with_runs(self.tmp)

    def plugin(self, name, **kwargs):
        return {p["name"]: p for p in bc.build(self.root, **kwargs)["plugins"]}[name]


class Shape(Fixture):
    def test_the_header_comes_from_the_manifests_and_the_board(self):
        catalog = bc.build(self.root)
        self.assertEqual(catalog["schemaVersion"], 1)
        self.assertEqual(catalog["marketplace"], {"name": "eurus-labs", "version": "9.9.9", "source": "eurus-labs/Skills"})
        self.assertEqual(catalog["hosts"], [{"id": "copilot", "label": "Copilot CLI"}, {"id": "claude", "label": "Claude Code"}])
        self.assertNotIn("exe", json.dumps(catalog["hosts"]))

    def test_plugins_keep_the_marketplace_order_and_its_text(self):
        catalog = bc.build(self.root)
        self.assertEqual([p["name"] for p in catalog["plugins"]], ["beta", "alpha"])
        self.assertEqual(self.plugin("alpha")["description"], "First.")
        self.assertEqual(self.plugin("alpha")["version"], "1.0.0")
        self.assertEqual([s["name"] for s in self.plugin("alpha")["skills"]], ["one", "two"])

    def test_a_plugin_without_cases_still_lists_its_skills(self):
        beta = self.plugin("beta")
        self.assertEqual(beta["cases"], [])
        self.assertEqual(beta["skills"][0]["evals"], {"cases": 0, "hosts": {}})

    def test_case_kinds(self):
        kinds = {c["name"]: c["kind"] for c in self.plugin("alpha")["cases"]}
        self.assertEqual(kinds, {"one-fires": "fires", "one-quiet": "quiet", "two-works": "behavior"})

    def test_a_case_that_fires_one_skill_and_forbids_another_is_fires(self):
        put(os.path.join(self.root, "plugins", "alpha", "evals", "trigger", "one-fires", "graders", "h.md"),
            QUIET % "two")
        kinds = {c["name"]: c["kind"] for c in self.plugin("alpha")["cases"]}
        self.assertEqual(kinds["one-fires"], "fires")


class Scores(Fixture):
    def test_a_skill_takes_each_cases_newest_trusted_run_and_averages_them(self):
        one = self.plugin("alpha")["skills"][0]["evals"]
        self.assertEqual(one["cases"], 2)
        # one-fires: 01-04 is partial, so 01-02 (0.6) counts; one-quiet: 0.5. Mean 0.55.
        self.assertEqual(one["hosts"]["claude"], {"cases": 2, "score": 0.55, "latest": "2026-01-02T00-00-00Z"})
        self.assertEqual(one["hosts"]["copilot"], {"cases": 1, "score": 0.9, "latest": "2026-01-03T00-00-00Z"})

    def test_a_host_with_no_trusted_run_is_left_out(self):
        two = self.plugin("alpha")["skills"][1]["evals"]
        self.assertEqual(list(two["hosts"]), ["claude"])
        self.assertEqual(two["hosts"]["claude"]["score"], 0.8)

    def test_an_untrusted_run_is_in_the_case_but_not_in_the_skill(self):
        fires = {c["name"]: c for c in self.plugin("alpha")["cases"]}["one-fires"]
        self.assertEqual(fires["latest"]["claude"], {"stamp": "2026-01-04T00-00-00Z", "score": 0.1, "runs": 1, "trusted": False})
        self.assertTrue(fires["latest"]["copilot"]["trusted"])
        self.assertEqual(fires["skills"], ["one"])

    def test_an_errored_run_and_skipped_judges_are_untrusted_too(self):
        archive(self.root, "2026-01-05T00-00-00Z", [case_doc("two-works", 1.0, error="timed out after 300s")])
        two = self.plugin("alpha")["skills"][1]["evals"]["hosts"]["claude"]
        self.assertEqual(two["score"], 0.8)
        latest = {c["name"]: c for c in self.plugin("alpha")["cases"]}["two-works"]["latest"]["claude"]
        self.assertFalse(latest["trusted"])

    def test_runs_are_one_entry_per_result_file_oldest_first(self):
        self.assertEqual(self.plugin("alpha")["runs"], [
            {"stamp": "2026-01-01T00-00-00Z", "host": "claude", "score": 0.77, "cases": 3},
            {"stamp": "2026-01-02T00-00-00Z", "host": "claude", "score": 0.6, "cases": 1},
            {"stamp": "2026-01-03T00-00-00Z", "host": "copilot", "score": 0.9, "cases": 1},
            {"stamp": "2026-01-04T00-00-00Z", "host": "claude", "score": 0.1, "cases": 1}])

    def test_a_run_only_in_results_does_not_change_the_committed_catalog(self):
        before = bc.render(bc.build(self.root))
        archive(self.root, "2026-02-01T00-00-00Z", [case_doc("one-fires", 0.0)], folder="results")
        self.assertEqual(bc.render(bc.build(self.root)), before)

    def test_the_skill_manager_view_adds_the_local_runs(self):
        archive(self.root, "2026-02-01T00-00-00Z", [case_doc("one-fires", 0.0)], folder="results")
        catalog = bc.build(self.root, include_local=True)
        alpha = {p["name"]: p for p in catalog["plugins"]}["alpha"]
        self.assertEqual(alpha["runs"][-1]["stamp"], "2026-02-01T00-00-00Z")
        self.assertEqual(alpha["skills"][0]["evals"]["hosts"]["claude"]["score"], 0.25)  # (0.0 + 0.5) / 2


class Featured(Fixture):
    def write(self, doc):
        put_json(os.path.join(self.root, "tools", "featured.json"), doc)

    def test_no_file_means_null(self):
        self.assertIsNone(bc.build(self.root)["featured"])

    def test_a_named_plugin_is_carried_over(self):
        doc = {"plugin": "alpha", "note": "New", "text": "Hello."}
        self.write(doc)
        self.assertEqual(bc.build(self.root)["featured"], doc)

    def test_an_unknown_plugin_fails_the_build_and_says_why(self):
        self.write({"plugin": "nope", "note": "New", "text": "Hello."})
        with self.assertRaisesRegex(bc.CatalogError, "'nope'.*not in the marketplace"):
            bc.build(self.root)
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(bc.main([], self.root), 1)
        self.assertIn("nope", err.getvalue())
        self.assertFalse(os.path.exists(os.path.join(self.root, "catalog.json")))

    def test_a_featured_file_missing_a_key_fails(self):
        self.write({"plugin": "alpha", "note": "New"})
        with self.assertRaises(bc.CatalogError):
            bc.build(self.root)


class Output(Fixture):
    def run_main(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = bc.main(list(argv), self.root)
        return code, out.getvalue()

    def read(self):
        with open(os.path.join(self.root, "catalog.json"), "rb") as fh:
            return fh.read()

    def test_writing_twice_changes_no_byte_and_holds_no_time(self):
        self.assertEqual(self.run_main()[0], 0)
        first = self.read()
        self.assertEqual(self.run_main()[0], 0)
        self.assertEqual(self.read(), first)
        self.assertTrue(first.endswith(b"}\n"))
        self.assertIn(b'\n  "hosts": [', first)  # sorted keys, 2-space indentation
        self.assertNotIn(b"generated", first.lower())

    def test_check_passes_on_a_fresh_file_and_writes_nothing(self):
        self.run_main()
        before = self.read()
        code, out = self.run_main("--check")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.read(), before)

    def test_check_fails_when_the_file_is_missing(self):
        code, out = self.run_main("--check")
        self.assertEqual(code, 1)
        self.assertIn("python3 tools/build_catalog.py", out)
        self.assertFalse(os.path.exists(os.path.join(self.root, "catalog.json")))

    def test_check_fails_after_a_skill_description_changes_and_names_the_fix(self):
        self.run_main()
        put(os.path.join(self.root, "plugins", "alpha", "skills", "one", "SKILL.md"),
            "---\nname: one\ndescription: Does something else now.\n---\n")
        code, out = self.run_main("--check")
        self.assertEqual(code, 1)
        self.assertIn("python3 tools/build_catalog.py", out)

    def test_check_fails_after_a_new_archived_run(self):
        self.run_main()
        archive(self.root, "2026-03-01T00-00-00Z", [case_doc("two-works", 0.1)])
        self.assertEqual(self.run_main("--check")[0], 1)


class Repository(unittest.TestCase):
    def test_this_repository_has_nine_plugins_and_eighteen_skills(self):
        catalog = bc.build()
        self.assertEqual((len(catalog["plugins"]), sum(len(p["skills"]) for p in catalog["plugins"])), (9, 18))

    def test_the_committed_catalog_is_current(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = bc.main(["--check"])
        self.assertEqual(code, 0, out.getvalue())

    def test_the_committed_catalog_is_small_and_names_are_safe(self):
        path = os.path.join(bc.REPO, "catalog.json")
        self.assertLess(os.path.getsize(path), 1024 * 1024)
        catalog = bc.build()
        for plugin in catalog["plugins"]:
            self.assertRegex(plugin["name"], r"^[a-z0-9][a-z0-9-]*$")
            for case in plugin["cases"]:
                self.assertRegex(case["name"], r"^[a-z0-9][a-z0-9-]*$")

    def test_a_changed_skill_description_in_a_copy_of_this_repository_fails_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            for part in ("plugins", ".github", "tools", "catalog.json"):
                src = os.path.join(bc.REPO, part)
                if os.path.isdir(src):
                    shutil.copytree(src, os.path.join(tmp, part),
                                    ignore=shutil.ignore_patterns("report.html", "__pycache__", "test_*.py", "*.pyc"))
                else:
                    shutil.copy(src, tmp)
            skill = os.path.join(tmp, "plugins", "planning", "skills", "analyze-requirements", "SKILL.md")
            with open(skill, encoding="utf-8") as fh:
                text = fh.read()
            self.assertIn("description:", text)
            with open(skill, "w", encoding="utf-8") as fh:
                fh.write(text.replace("description:", "description: Changed. ", 1))
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(bc.main(["--check"], tmp), 1)
            self.assertIn("python3 tools/build_catalog.py", out.getvalue())


if __name__ == "__main__":
    unittest.main()
