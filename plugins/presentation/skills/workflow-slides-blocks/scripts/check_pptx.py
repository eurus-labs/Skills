#!/usr/bin/env python3
"""Check that a saved .pptx is a well-formed package, and which slides changed against the original.

Standard library only. Read-only. A gate: human-readable lines, exit 0 when the package is sound.

    python3 check_pptx.py out.pptx
    python3 check_pptx.py out.pptx --original in.pptx

Checks every XML part parses, every part has a content type, every internal relationship points at a
part that exists, and every slide in the slide list resolves. With --original it also reports the slide
count and lists each slide whose XML differs, so you can confirm only the slides you meant to change did.
"""

import hashlib
import posixpath
import sys
import zipfile
import xml.etree.ElementTree as ET

CT = "{http://schemas.openxmlformats.org/package/2006/content-types}"
REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"
P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"


def source_of(rels_path):
    """The part a .rels file describes: ppt/slides/_rels/slide1.xml.rels -> ppt/slides/slide1.xml."""
    folder, name = posixpath.split(rels_path)
    return posixpath.join(posixpath.dirname(folder), name[:-len(".rels")])


def check_package(z):
    errors = []
    names = set(z.namelist())
    if "[Content_Types].xml" not in names:
        return ["no [Content_Types].xml"], []
    types = ET.fromstring(z.read("[Content_Types].xml"))
    defaults = {d.get("Extension").lower() for d in types.findall(CT + "Default")}
    overrides = {o.get("PartName").lstrip("/") for o in types.findall(CT + "Override")}
    for name in sorted(names):
        if name.endswith("/"):
            continue
        if name != "[Content_Types].xml":
            ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
            if name not in overrides and ext not in defaults:
                errors.append("no content type for %s" % name)
        if name.endswith((".xml", ".rels")):
            try:
                ET.fromstring(z.read(name))
            except ET.ParseError as exc:
                errors.append("%s does not parse: %s" % (name, exc))
    for over in sorted(overrides - names):
        errors.append("content type for a part that does not exist: /%s" % over)
    for rels in sorted(n for n in names if n.endswith(".rels")):
        try:
            root = ET.fromstring(z.read(rels))
        except ET.ParseError:
            continue
        base = posixpath.dirname(source_of(rels)) if rels != "_rels/.rels" else ""
        for rel in root.findall(REL + "Relationship"):
            if rel.get("TargetMode") == "External":
                continue
            target = rel.get("Target")
            part = target.lstrip("/") if target.startswith("/") else \
                posixpath.normpath(posixpath.join(base, target))
            if part not in names:
                errors.append("%s: %s -> %s, which does not exist" % (rels, rel.get("Id"), part))
    return errors, slide_parts(z, errors)


def slide_parts(z, errors):
    """The slide parts in deck order; records an error for any slide id that does not resolve."""
    try:
        pres = ET.fromstring(z.read("ppt/presentation.xml"))
        rels = ET.fromstring(z.read("ppt/_rels/presentation.xml.rels"))
    except KeyError as exc:
        errors.append("missing %s" % exc)
        return []
    targets = {r.get("Id"): posixpath.normpath(posixpath.join("ppt", r.get("Target")))
               for r in rels.findall(REL + "Relationship")}
    order = []
    lst = pres.find(P + "sldIdLst")
    for sld in (lst if lst is not None else []):
        rid = sld.get(R + "id")
        if rid not in targets:
            errors.append("slide id %s has no relationship %s" % (sld.get("id"), rid))
            continue
        order.append(targets[rid])
    return order


def digests(z, parts):
    return [hashlib.sha256(z.read(p)).hexdigest() if p in z.namelist() else None for p in parts]


def main(argv):
    if not argv or len(argv) not in (1, 3) or (len(argv) == 3 and argv[1] != "--original"):
        print("usage: check_pptx.py <out.pptx> [--original <in.pptx>]", file=sys.stderr)
        return 2
    try:
        out = zipfile.ZipFile(argv[0])
    except (OSError, zipfile.BadZipFile) as exc:
        print("FAIL %s is not a zip package: %s" % (argv[0], exc))
        return 1
    with out:
        bad = out.testzip()
        errors, order = check_package(out)
        if bad:
            errors.insert(0, "corrupt member %s" % bad)
        for e in errors:
            print("FAIL " + e)
        print("%s: %d slide(s), %s" % (argv[0], len(order),
                                      "package OK" if not errors else "%d problem(s)" % len(errors)))
        if len(argv) == 3:
            try:
                with zipfile.ZipFile(argv[2]) as orig:
                    o_errors = []
                    o_order = slide_parts(orig, o_errors)
                    before = digests(orig, o_order)
            except (OSError, zipfile.BadZipFile) as exc:
                print("FAIL original %s is not readable: %s" % (argv[2], exc))
                return 1
            after = digests(out, order)
            if len(before) != len(after):
                print("NOTE slide count changed: %d -> %d" % (len(before), len(after)))
            changed = [i + 1 for i in range(min(len(before), len(after))) if before[i] != after[i]]
            print("changed slides: %s" % (", ".join(map(str, changed)) or "none"))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
