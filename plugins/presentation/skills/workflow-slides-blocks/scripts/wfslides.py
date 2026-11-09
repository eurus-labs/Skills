"""wfslides — helpers for simple block-style workflow slides (python-pptx).

Grid: 1920 x 1080 px; 1 pt = 2 px on this grid. Import it from a build script:

    import sys; sys.path.insert(0, "<this folder>")
    from wfslides import Canvas, read_theme

Requires python-pptx, lxml and Pillow, which this script never installs; see the skill's
Requirements. `python3 wfslides.py --check-deps` reports whether they are present.
"""
import os, re, glob, sys


def _check_deps():
    """Print which required packages are present; exit 1 if any is missing."""
    import importlib
    missing = []
    for module, package in (("pptx", "python-pptx"), ("lxml", "lxml"), ("PIL", "Pillow")):
        try:
            mod = importlib.import_module(module)
            print("ok      %s %s" % (package, getattr(mod, "__version__", "")))
        except ImportError:
            print("missing %s" % package)
            missing.append(package)
    if missing:
        print("install: python3 -m pip install %s" % " ".join(missing), file=sys.stderr)
        return 1
    return 0


# Run as a script it only checks the requirements, before anything below needs them: the class
# definitions use python-pptx at definition time, so on the machine this check is for, getting
# that far would crash instead of reporting.
if __name__ == "__main__":
    if sys.argv[1:] != ["--check-deps"]:
        sys.exit("usage: python3 wfslides.py --check-deps   (otherwise import it from a build script)")
    sys.exit(_check_deps())

try:
    from pptx.util import Emu, Pt
    from pptx.dml.color import RGBColor
    from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
    from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
    from pptx.oxml.ns import qn
    from lxml import etree
    from PIL import ImageFont
except ImportError as exc:  # a required dependency, never installed from here
    sys.exit("wfslides: missing %s. Install python-pptx and Pillow yourself "
             "(python3 -m pip install python-pptx Pillow), then run again." % (exc.name or exc))

INK, MUTED, LINE, LIGHT = "1A1D24", "5B6270", "D9DDE2", "F5F7F9"
DEFAULT = {"primary": "0F4C81", "second": "12807A", "accent": "EF7A22"}

# Outline icons drawn as native shapes, for when no icon PNGs are available: vector, editable in
# PowerPoint, and nothing to install. Pass the name where a PNG path would go.
SHAPE_ICONS = {
    "document": "FLOWCHART_DOCUMENT", "documents": "FLOWCHART_MULTIDOCUMENT", "note": "FOLDED_CORNER",
    "database": "CAN", "archive": "FLOWCHART_MAGNETIC_DISK", "decide": "DIAMOND", "cloud": "CLOUD",
    "config": "GEAR_6", "loop": "CIRCULAR_ARROW", "feedback": "OVAL_CALLOUT", "speed": "LIGHTNING_BOLT",
    "target": "DONUT", "risk": "ISOSCELES_TRIANGLE", "stop": "OCTAGON", "start": "FLOWCHART_TERMINATOR",
    "process": "FLOWCHART_PREDEFINED_PROCESS", "package": "CUBE", "user": "SMILEY_FACE", "idea": "SUN",
}

def read_theme(prs):
    """Return {'major','minor','accents':[hex..]} from the deck theme."""
    part = prs.slide_masters[0].part.part_related_by(
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme")
    x = part.blob.decode("utf8", "ignore")
    major = re.search(r'<a:majorFont><a:latin typeface="([^"]*)"', x)
    minor = re.search(r'<a:minorFont><a:latin typeface="([^"]*)"', x)
    acc = re.findall(r'<a:accent\d><a:srgbClr val="([0-9A-Fa-f]{6})"', x)
    return {"major": major.group(1) if major else "", "minor": minor.group(1) if minor else "", "accents": acc}

def _font_file(bold):
    pats = ["*LiberationSans-Bold.ttf" if bold else "*LiberationSans-Regular.ttf",
            "*DejaVuSans-Bold.ttf" if bold else "*DejaVuSans.ttf"]
    for p in pats:
        hits = glob.glob("/usr/share/fonts/**/" + p, recursive=True)
        if hits: return hits[0]
    return None

class Canvas:
    def __init__(self, prs, slide, palette=None, font="+mj-lt"):
        self.prs, self.s = prs, slide
        self.K = prs.slide_width / 1920
        self.P = dict(DEFAULT, **(palette or {}))
        self.font = font
        self.texts, self.lines, self.objs, self.warnings = [], [], [], []

    # ---------- basics ----------
    def E(self, v): return Emu(int(v * self.K))
    def clear(self, drop_media=True):
        tree = self.s.shapes._spTree
        for el in list(tree):
            if el.tag.split('}')[1] not in ('nvGrpSpPr', 'grpSpPr'): tree.remove(el)
        if drop_media:
            for rId, rel in list(self.s.part.rels.items()):
                if rel.reltype.endswith('/image') or 'diagram' in rel.reltype: self.s.part.drop_rel(rId)
        self.s.background.fill.solid(); self.s.background.fill.fore_color.rgb = RGBColor.from_string("FFFFFF")
    def _nostyle(self, sh):
        st = sh._element.find(qn('p:style'))
        if st is not None: sh._element.remove(st)

    # ---------- measuring ----------
    def fit(self, txt, width_px, size_pt, bold=False):
        """Number of lines `txt` needs in width_px (greedy word wrap)."""
        f = _font_file(bold)
        font = ImageFont.truetype(f, int(size_pt * 2)) if f else None
        meas = (lambda t: font.getlength(t)) if font else (lambda t: len(t) * size_pt * 2 * 0.58)
        lines, cur = 1, ""
        for w in txt.split():
            t = (cur + " " + w).strip()
            if meas(t) <= width_px or not cur: cur = t
            else: lines += 1; cur = w
        return lines

    # ---------- shapes ----------
    def box(self, x, y, w, h, fill=None, line=None, lw=1.2, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=None, dash=False, name=None):
        E = self.E; sh = self.s.shapes.add_shape(shape, E(x), E(y), E(w), E(h))
        if fill: sh.fill.solid(); sh.fill.fore_color.rgb = RGBColor.from_string(fill)
        else: sh.fill.background()
        if line:
            sh.line.color.rgb = RGBColor.from_string(line); sh.line.width = E(lw)
            if dash: etree.SubElement(sh.line._get_or_add_ln(), qn('a:prstDash')).set('val', 'dash')
        else: sh.line.fill.background()
        self._nostyle(sh)
        if radius is not None and shape == MSO_SHAPE.ROUNDED_RECTANGLE: sh.adjustments[0] = radius / min(w, h)
        if name: sh.name = name
        return sh

    def text(self, x, y, w, h, paras, size=13, color=INK, bold=False, align=PP_ALIGN.LEFT,
             anchor=MSO_ANCHOR.TOP, shape=None, spacing=1.05, max_lines=None, track=True):
        """paras: list of str or list of (text, {size,bold,color}) runs.
        track=False ONLY for text inside shapes (badges, chips)."""
        E = self.E
        if shape is None: shape = self.s.shapes.add_textbox(E(x), E(y), E(w), E(h))
        tf = shape.text_frame; tf.word_wrap = True; tf.vertical_anchor = anchor
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        used = 0
        for i, para in enumerate(paras):
            runs = [(para, {})] if isinstance(para, str) else para
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph(); p.alignment = align
            if spacing: p.line_spacing = spacing
            for t, o in runs:
                r = p.add_run(); r.text = t; f = r.font; f.name = self.font
                f.size = Pt(o.get('size', size)); f.bold = o.get('bold', bold)
                f.color.rgb = RGBColor.from_string(o.get('color', color))
            if w > 0:
                full = "".join(t for t, _ in runs); sz = max(o.get('size', size) for _, o in runs)
                n = self.fit(full, w, sz, any(o.get('bold', bold) for _, o in runs)); used += n * sz * 2 * 1.15
                if max_lines and n > max_lines: self.warnings.append(f"WRAP: '{full}' needs {n} lines (max {max_lines})")
        if w > 0 and h > 0 and used > h * 1.25: self.warnings.append(f"OVERFLOW: text at ({x},{y}) needs ~{int(used)}px, box {h}px: {paras}")
        if track and w > 0: self.texts.append((x, y, x + w, y + max(h, used), str(paras)[:40]))
        return shape

    def line(self, x1, y1, x2, y2, color=INK, w=1.5, head=True, dash=False):
        E = self.E; c = self.s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, E(x1), E(y1), E(x2), E(y2))
        c.line.color.rgb = RGBColor.from_string(color); c.line.width = E(w); self._nostyle(c)
        ln = c.line._get_or_add_ln()
        if dash: etree.SubElement(ln, qn('a:prstDash')).set('val', 'dash')
        if head: etree.SubElement(ln, qn('a:tailEnd')).set('type', 'triangle')
        self.lines.append((x1, y1, x2, y2))

    def poly(self, pts, color=INK, dash=False):
        for i, (a, b) in enumerate(zip(pts, pts[1:])): self.line(*a, *b, color=color, head=i == len(pts) - 2, dash=dash)

    def icon(self, path, cx, cy, d=56, alt=None):
        """`path` is a PNG file, or one of SHAPE_ICONS when no icon files are available."""
        if not os.path.isfile(path):
            if path not in SHAPE_ICONS:
                raise ValueError("icon %r is neither a file nor a shape icon (%s)"
                                 % (path, ", ".join(sorted(SHAPE_ICONS))))
            sh = self.box(cx - d / 2, cy - d / 2, d, d, fill="FFFFFF", line=INK, lw=2.5,
                          shape=getattr(MSO_SHAPE, SHAPE_ICONS[path]), name="Icon " + (alt or path))
            sh._element.nvSpPr.cNvPr.set('descr', alt or path)
            self.objs.append((cx - d / 2, cy - d / 2, cx + d / 2, cy + d / 2, 'icon ' + (alt or path)))
            return sh
        E = self.E; pic = self.s.shapes.add_picture(path, E(cx - d / 2), E(cy - d / 2), E(d), E(d))
        pic._element.nvPicPr.cNvPr.set('descr', alt or os.path.basename(path))
        self.objs.append((cx - d / 2, cy - d / 2, cx + d / 2, cy + d / 2, 'icon ' + (alt or os.path.basename(path))))
        return pic

    # ---------- composites ----------
    def title(self, t, sub=None, page=None):
        self.text(36, 44, 1840, 50, [t.upper()], size=26, bold=True, max_lines=1)
        if sub: self.text(36, 114, 1840, 32, [sub], size=15, color=MUTED, max_lines=1)
        if page: self.text(1760, 1010, 120, 30, [page], size=12, bold=True, color=MUTED, align=PP_ALIGN.RIGHT, track=False)

    def block(self, x, y, w, h, title, color, num=None, dash=True):
        self.box(x, y, w, h, line=color, radius=24, dash=dash, name=f"Block {title}")
        tx = x + 24
        if num is not None:
            b = self.box(x + 20, y + 18, 28, 28, fill=color, shape=MSO_SHAPE.OVAL, name=f"Badge {num}")
            self.text(0, 0, 0, 0, [str(num)], size=13, bold=True, color="FFFFFF", align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, shape=b, track=False)
            tx = x + 58
        self.text(tx, y + 18, w - (tx - x) - 20, 28, [title.upper()], size=14, bold=True, color=color, anchor=MSO_ANCHOR.MIDDLE, max_lines=1)

    def vnode(self, cx, cy, icon, label, sub=(), w=220, ts=14, ss=11.5, d=56):
        self.icon(icon, cx, cy, d, alt=label)
        paras = [[(label, {'bold': True, 'size': ts})]] + [[(l, {'size': ss, 'color': MUTED})] for l in sub]
        h = int((2 * ts + len(sub) * ss) * 2 * 1.15) + 4
        self.text(cx - w / 2, cy + d / 2 + 8, w, h, paras, align=PP_ALIGN.CENTER, max_lines=2)

    def hnode(self, cx, cy, icon, label, sub=(), w=320, ts=16, ss=12.5, d=56):
        self.icon(icon, cx, cy, d, alt=label)
        paras = [[(label, {'bold': True, 'size': ts})]] + [[(l, {'size': ss, 'color': MUTED})] for l in sub]
        self.text(cx + d / 2 + 16, cy - 34, w, 90, paras, anchor=MSO_ANCHOR.MIDDLE, max_lines=2)

    def chip_for(self, cx, cy, num, color, d=56):
        """Step chip at the top-left corner of the icon centred at (cx, cy)."""
        self.chip(cx - d / 2 - 2, cy - d / 2 - 2, num, color)

    def chip(self, cx, cy, num, color):
        self.objs.append((cx - 13, cy - 13, cx + 13, cy + 13, f'chip {num}'))
        b = self.box(cx - 13, cy - 13, 26, 26, fill="FFFFFF", line=color, lw=1.5, shape=MSO_SHAPE.OVAL, name=f"Step {num}")
        self.text(0, 0, 0, 0, [str(num)], size=11, bold=True, color=color, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, shape=b, track=False)

    def takeaway(self, t, icons=(), y=905):
        x = 620
        for i, ic in enumerate(icons): self.icon(ic, x + i * 48, y + 20, 38)
        self.text(x + 48 * len(icons), y, 1200, 40, [t], size=16, bold=True, color=INK, anchor=MSO_ANCHOR.MIDDLE, max_lines=1)

    def notes(self, t, replace=False):
        """Add `t` to the slide's speaker notes, after any already there; they are the user's.
        replace=True only when the user asked for their notes to be replaced."""
        tf = self.s.notes_slide.notes_text_frame
        if replace or not tf.text.strip():
            tf.text = t
            return
        tf.add_paragraph()  # a blank line between their notes and the moved text
        for line in t.split("\n"):
            tf.add_paragraph().text = line

    # ---------- QA ----------
    def check(self):
        """Warn when a connector crosses a text box, or a text box overlaps an icon/chip.
        Every free text is tracked; only text inside shapes (badges, chips) is skipped. Call before saving."""
        def seg_hits(r, l):
            x1, y1, x2, y2 = l; rx1, ry1, rx2, ry2 = r[:4]
            for k in range(41):
                px, py = x1 + (x2 - x1) * k / 40, y1 + (y2 - y1) * k / 40
                if rx1 - 4 < px < rx2 + 4 and ry1 + 2 < py < ry2 - 2: return True
            return False
        def overlap(a, b):
            return min(a[2], b[2]) - max(a[0], b[0]) > 4 and min(a[3], b[3]) - max(a[1], b[1]) > 4
        for l in self.lines:
            for r in self.texts:
                if seg_hits(r, l): self.warnings.append(f"CROSS: line {tuple(int(v) for v in l)} crosses text {r[4]}")
        for o in self.objs:
            for r in self.texts:
                if overlap(o, r): self.warnings.append(f"OVERLAP: {o[4]} overlaps text {r[4]}")
        return self.warnings
