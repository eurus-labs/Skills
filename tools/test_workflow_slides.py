#!/usr/bin/env python3
"""Behavioural tests for the presentation plugin's workflow-slides-blocks scripts.

slide_text.py and check_pptx.py are standard library only, and are tested on decks this file writes
with zipfile. wfslides.py requires python-pptx (the declared exception in
.github/instructions/domain/scripts.instructions.md): its missing-dependency path is tested always,
and its drawing and check() only where python-pptx is installed, which CI ensures.

Stdlib only, no test framework -- see tools/test_check_env.py for why.

    python3 tools/test_workflow_slides.py
"""

import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(REPO, "plugins", "presentation", "skills", "workflow-slides-blocks", "scripts")

FAILURES = []


def check(name, condition, detail=""):
    if condition:
        print("ok   %s" % name)
    else:
        print("FAIL %s %s" % (name, detail))
        FAILURES.append(name)


def run(script, *args, **kw):
    return subprocess.run([sys.executable, os.path.join(SCRIPTS, script)] + list(args),
                          capture_output=True, text=True, **kw)


CT_HEAD = ('<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/'
           'package/2006/content-types"><Default Extension="rels" ContentType="application/'
           'vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" '
           'ContentType="application/xml"/>')
RELS = ('<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/'
        'package/2006/relationships">%s</Relationships>')
REL = '<Relationship Id="%s" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/%s" Target="%s"/>'
SLIDE = ('<?xml version="1.0" encoding="UTF-8"?><p:sld xmlns:p="http://schemas.openxmlformats.org/'
         'presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
         '<p:cSld><p:spTree>%s</p:spTree></p:cSld></p:sld>')
PARA = '<p:sp><p:txBody><a:p><a:r><a:t>%s</a:t></a:r></a:p></p:txBody></p:sp>'


def write_deck(path, texts, notes=None, break_rel=False, drop_type=False):
    """A minimal deck: presentation.xml, one slide part per text, optional notes on slide 1."""
    files = {}
    ids, prels = [], []
    for i, text in enumerate(texts, start=1):
        files["ppt/slides/slide%d.xml" % i] = SLIDE % (PARA % text)
        ids.append('<p:sldId id="%d" r:id="rId%d"/>' % (255 + i, i))
        prels.append(REL % ("rId%d" % i, "slide", "slides/slide%d.xml" % i))
    if notes:
        files["ppt/notesSlides/notesSlide1.xml"] = SLIDE.replace("p:sld ", "p:notes ").replace(
            "</p:sld>", "</p:notes>") % (PARA % "1" + PARA % notes)
        files["ppt/slides/_rels/slide1.xml.rels"] = RELS % (
            REL % ("rId9", "notesSlide", "../notesSlides/notesSlide%d.xml" % (2 if break_rel else 1)))
    files["ppt/presentation.xml"] = (
        '<?xml version="1.0" encoding="UTF-8"?><p:presentation xmlns:p="http://schemas.openxmlformats.org/'
        'presentationml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/'
        'relationships"><p:sldIdLst>%s</p:sldIdLst></p:presentation>' % "".join(ids))
    files["ppt/_rels/presentation.xml.rels"] = RELS % "".join(prels)
    files["_rels/.rels"] = RELS % (REL % ("rId1", "officeDocument", "ppt/presentation.xml"))
    files["docProps/thumb.jpeg"] = "not really a jpeg"
    ct = CT_HEAD + ("" if drop_type else '<Default Extension="jpeg" ContentType="image/jpeg"/>')
    files["[Content_Types].xml"] = ct + "</Types>"
    with zipfile.ZipFile(path, "w") as z:
        for name, data in files.items():
            z.writestr(name, data)


def stdlib_tests(tmp):
    deck = os.path.join(tmp, "deck.pptx")
    write_deck(deck, ["Intro", "Review process: draft, review, fix", "Next"], notes="Say why first")

    out = run("slide_text.py", deck)
    check("slide_text prints every slide's text in deck order",
          out.returncode == 0 and out.stdout.index("Intro") < out.stdout.index("Review process")
          < out.stdout.index("Next"), out.stdout + out.stderr)
    check("slide_text prints the notes and drops the slide-number placeholder",
          "[Notes] Say why first" in out.stdout, out.stdout)
    bad = os.path.join(tmp, "not.pptx")
    with open(bad, "w") as fh:
        fh.write("plain text")
    out = run("slide_text.py", bad)
    check("slide_text fails loudly on a file that is not a .pptx",
          out.returncode == 1 and "not a readable .pptx" in out.stderr, out.stderr)

    out = run("check_pptx.py", deck)
    check("check_pptx accepts a well-formed package", out.returncode == 0 and "package OK" in out.stdout,
          out.stdout)

    broken = os.path.join(tmp, "broken.pptx")
    write_deck(broken, ["Intro"], notes="x", break_rel=True)
    out = run("check_pptx.py", broken)
    check("check_pptx fails a relationship to a part that does not exist",
          out.returncode == 1 and "notesSlide2.xml, which does not exist" in out.stdout, out.stdout)

    untyped = os.path.join(tmp, "untyped.pptx")
    write_deck(untyped, ["Intro"], drop_type=True)
    out = run("check_pptx.py", untyped)
    check("check_pptx fails a part with no content type",
          out.returncode == 1 and "no content type for docProps/thumb.jpeg" in out.stdout, out.stdout)

    edited = os.path.join(tmp, "edited.pptx")
    write_deck(edited, ["Intro", "REVIEW PROCESS", "Next"], notes="Say why first")
    out = run("check_pptx.py", edited, "--original", deck)
    check("check_pptx lists exactly the slides that changed",
          out.returncode == 0 and "changed slides: 2\n" in out.stdout, out.stdout)
    shorter = os.path.join(tmp, "shorter.pptx")
    write_deck(shorter, ["Intro", "Review process: draft, review, fix"], notes="Say why first")
    out = run("check_pptx.py", shorter, "--original", deck)
    check("check_pptx reports a changed slide count",
          "slide count changed: 3 -> 2" in out.stdout, out.stdout)


def missing_dependency_test():
    # Block python-pptx whether or not it is installed: importing wfslides must stop with the
    # install command, never fall through to a NameError later.
    code = ("import sys; sys.modules['pptx'] = None; sys.path.insert(0, %r); import wfslides"
            % SCRIPTS)
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    check("wfslides stops at import with the install command when python-pptx is missing",
          out.returncode != 0 and "pip install python-pptx Pillow" in out.stderr
          and "Traceback" not in out.stderr, out.stderr)
    code = ("import sys, runpy; sys.modules['pptx'] = None; sys.argv = ['wfslides.py', '--check-deps'];"
            " runpy.run_path(%r, run_name='__main__')" % os.path.join(SCRIPTS, "wfslides.py"))
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    check("wfslides --check-deps reports the missing package and exits 1",
          out.returncode == 1 and "missing python-pptx" in out.stdout, out.stdout + out.stderr)


def drawing_tests(tmp):
    try:
        import pptx  # noqa: F401
        import PIL  # noqa: F401
    except ImportError:
        print("skip: python-pptx or Pillow not installed; CI installs them")
        return
    sys.path.insert(0, SCRIPTS)
    from pptx import Presentation
    from pptx.util import Inches
    import wfslides

    def canvas():
        prs = Presentation()
        prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        return prs, wfslides.Canvas(prs, slide)

    prs, c = canvas()
    c.title("Review process", sub="Draft, review, fix")
    c.block(70, 170, 770, 690, "Loop", c.P["second"], num=1)
    c.vnode(300, 450, "config", "Review")
    c.vnode(600, 450, "loop", "Fix")
    c.chip_for(300, 450, 1, c.P["second"])
    c.line(340, 450, 560, 450)
    check("a clean layout with shape icons draws with no warnings", c.check() == [], c.warnings)
    path = os.path.join(tmp, "built.pptx")
    prs.save(path)
    out = run("check_pptx.py", path)
    check("a deck saved through wfslides passes check_pptx", out.returncode == 0, out.stdout)

    _, c = canvas()
    c.vnode(300, 450, "config", "Review")
    c.chip(300, 500, 1, c.P["second"])  # by hand, onto the label
    check("check() reports a step chip placed over a label",
          any(w.startswith("OVERLAP: chip 1") for w in c.check()), c.warnings)

    _, c = canvas()
    c.text(400, 430, 200, 40, ["accepted"], size=12)
    c.line(300, 450, 700, 450)
    check("check() reports an arrow crossing a free label",
          any(w.startswith("CROSS") for w in c.check()), c.warnings)

    _, c = canvas()
    c.text(100, 100, 120, 30, ["a label far too long for its little box"], size=14, max_lines=1)
    check("text() reports a label that wraps past max_lines",
          any(w.startswith("WRAP") for w in c.warnings), c.warnings)

    _, c = canvas()
    try:
        c.icon("no-such-icon", 100, 100)
        raised = False
    except ValueError as exc:
        raised = "shape icon" in str(exc)
    check("an icon that is neither a file nor a shape icon is refused", raised)


def main():
    tmp = tempfile.mkdtemp(prefix="workflow-slides-")
    try:
        stdlib_tests(tmp)
        missing_dependency_test()
        drawing_tests(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print()
    if FAILURES:
        print("%d failure(s): %s" % (len(FAILURES), ", ".join(FAILURES)))
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
