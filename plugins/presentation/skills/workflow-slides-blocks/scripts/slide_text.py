#!/usr/bin/env python3
"""Print the text of every slide in a .pptx: shapes, speaker notes and SmartArt, in deck order.

Standard library only, so it runs before python-pptx is known to be present. Read-only.

    python3 slide_text.py deck.pptx            # human digest
    python3 slide_text.py deck.pptx --json     # one JSON object on stdout

Exit 0 on success, 1 if the file is not a readable .pptx.
"""

import json
import posixpath
import sys
import zipfile
import xml.etree.ElementTree as ET

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}
NOTES = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/notesSlide"
DIAGRAM_DATA = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/diagramData"
IMAGE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"


def rels_of(z, part):
    """{rId: (type, target part)} for `part`, targets resolved against its folder."""
    folder, name = posixpath.split(part)
    path = posixpath.join(folder, "_rels", name + ".rels")
    if path not in z.namelist():
        return {}
    found = {}
    for rel in ET.fromstring(z.read(path)).findall("rel:Relationship", NS):
        if rel.get("TargetMode") == "External":
            continue
        target = posixpath.normpath(posixpath.join(folder, rel.get("Target")))
        found[rel.get("Id")] = (rel.get("Type"), target)
    return found


def paragraphs(xml):
    """Each non-empty paragraph's text, in document order."""
    out = []
    for para in ET.fromstring(xml).iter("{%s}p" % NS["a"]):
        text = "".join(t.text or "" for t in para.iter("{%s}t" % NS["a"])).strip()
        if text:
            out.append(text)
    return out


def slides(path):
    with zipfile.ZipFile(path) as z:
        pres = "ppt/presentation.xml"
        rels = rels_of(z, pres)
        order = ET.fromstring(z.read(pres)).find("p:sldIdLst", NS)
        result = []
        for n, sld in enumerate(order if order is not None else [], start=1):
            part = rels[sld.get("{%s}id" % NS["r"])][1]
            srels = rels_of(z, part)
            entry = {"number": n, "part": part, "text": paragraphs(z.read(part)),
                     "notes": [], "smartart": [], "images": 0}
            for kind, target in srels.values():
                if kind == NOTES and target in z.namelist():
                    # Placeholders in the notes page repeat the slide number; keep the notes body.
                    entry["notes"] = [t for t in paragraphs(z.read(target)) if not t.isdigit()]
                elif kind == DIAGRAM_DATA and target in z.namelist():
                    entry["smartart"].extend(paragraphs(z.read(target)))
                elif kind == IMAGE:
                    entry["images"] += 1
            result.append(entry)
        return result


def main(argv):
    args = [a for a in argv if a != "--json"]
    if len(args) != 1:
        print("usage: slide_text.py <deck.pptx> [--json]", file=sys.stderr)
        return 1
    try:
        found = slides(args[0])
    except (OSError, KeyError, zipfile.BadZipFile, ET.ParseError) as exc:
        print("slide_text: %s is not a readable .pptx: %s" % (args[0], exc), file=sys.stderr)
        return 1
    if "--json" in argv:
        print(json.dumps({"slides": found}, ensure_ascii=False, indent=2))
        return 0
    for s in found:
        print("## Slide %d  (%s, %d image%s)" % (s["number"], s["part"], s["images"],
                                                 "" if s["images"] == 1 else "s"))
        for line in s["text"]:
            print("  " + line)
        if s["smartart"]:
            print("  [SmartArt] " + " | ".join(s["smartart"]))
        if s["notes"]:
            print("  [Notes] " + " ".join(s["notes"]))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
