"""Build the animated publication teasers into _includes/teasers/.

Each teaser is a 480x300 inline SVG. Colours come from CSS classes defined in
_sass/_teasers.scss (so light / dark mode is free) and timing from data-t
attributes played by assets/js/teasers.js. The markup on its own is the
finished picture: it is what shows without JS.

Every number drawn here is from the paper's abstract (or, for Cancer Letters
2026, which has no PubMed abstract, its introduction). Bars and curves without
numbers are schematic.

Run from the repo root:  python _teasers/build_teasers.py
"""
import math
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "_includes" / "teasers"
W, H = 480, 300


# --------------------------------------------------------------------------
# tiny SVG builder

STYLE_KEYS = ("font_size", "fill")   # CSS classes outrank presentation attributes


def attrs(d):
    out = []
    style = []
    for k in STYLE_KEYS:
        v = d.pop(k, None)
        if v is not None:
            style.append(f"{k.replace('_', '-')}:{v}{'px' if k == 'font_size' else ''}")
    if style:
        d["style"] = ";".join(style)
    if d.get("t") and d.get("opacity") is not None:
        d["fill_opacity"] = d["stroke_opacity"] = d.pop("opacity")
    for k, v in d.items():
        if v is None:
            continue
        if k == "cls":
            k = "class"
        elif k == "t":
            k = "data-t"
        elif k in ("dx", "dy", "mx", "my", "to", "path"):
            k = "data-" + k
        else:
            k = k.rstrip("_").replace("_", "-")
        out.append(f'{k}="{v}"')
    return " ".join(out)


def tag(name, inner=None, **a):
    if inner is None:
        return f"<{name} {attrs(a)}/>"
    if isinstance(inner, (list, tuple)):
        inner = "".join(inner)
    return f"<{name} {attrs(a)}>{inner}</{name}>"


def g(*children, **a):
    return tag("g", list(children), **a)


def rect(x, y, w, h, rx=0, **a):
    return tag("rect", x=r(x), y=r(y), width=r(w), height=r(h), rx=rx or None, **a)


def circle(cx, cy, rad, **a):
    return tag("circle", cx=r(cx), cy=r(cy), r=r(rad), **a)


def path(d, **a):
    return tag("path", d=d, **a)


def line(x1, y1, x2, y2, **a):
    return tag("line", x1=r(x1), y1=r(y1), x2=r(x2), y2=r(y2), **a)


def text(x, y, s, cls="lbl", anchor=None, **a):
    # the card shows the figure at about 0.6x, so small sizes are lifted to stay readable
    if a.get("font_size") is not None and a["font_size"] < 16:
        a["font_size"] += 2
    return tag("text", s, x=r(x), y=r(y), cls=cls, text_anchor=anchor, **a)


def tspan(s, cls):
    return f'<tspan class="{cls}">{s}</tspan>'


def r(v):
    return f"{v:.1f}".rstrip("0").rstrip(".") if isinstance(v, float) else str(v)


def caption(*parts, t="fade@.04-.1"):
    """Bottom line in the style of a slide title: (text, class) pairs.

    Kept quiet so it does not compete with the paper title beside it: the
    keywords (any part not marked f-ink) are set darker and bolder than the
    rest, with no accent colour.
    """
    inner = "".join(tspan(s, "cap-rest" if c == "f-ink" else "cap-key") for s, c in parts)
    return tag("text", inner, x=24, y=279, cls="cap", t=t)


def svg(key, label, body, poster=0.9):
    return (
        f'<svg class="teaser-anim t-{key}" viewBox="0 0 {W} {H}" role="img" '
        f'aria-label="{label}" data-poster="{poster}" focusable="false">'
        + rect(0, 0, W, H, cls="f-panel")
        # the whole scene fades out at the end of each loop so it can reset
        + g(*body, t="fade@0-.02 out@.96-1")
        + "</svg>"
    )


def smooth_closed(pts, tension=1.0):
    """Closed path through pts with rounded joins instead of corners."""
    n = len(pts)
    d = f"M{pts[0][0]:.1f} {pts[0][1]:.1f}"
    for i in range(n):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6 * tension, p1[1] + (p2[1] - p0[1]) / 6 * tension)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6 * tension, p2[1] - (p3[1] - p1[1]) / 6 * tension)
        d += f"C{c1[0]:.1f} {c1[1]:.1f} {c2[0]:.1f} {c2[1]:.1f} {p2[0]:.1f} {p2[1]:.1f}"
    return d + "Z"


def blob(cx, cy, rad, wobble, n, rnd, squash=1.0):
    """A soft irregular round outline, like a cell or spheroid edge."""
    pts = []
    for k in range(n):
        a = k / n * 2 * math.pi
        rr = rad + rnd.uniform(-wobble, wobble)
        pts.append((cx + rr * math.cos(a), cy + rr * squash * math.sin(a)))
    return smooth_closed(pts)


def drift(x0, y0, x1, y1, bend):
    """A gentle S-shaped path from (x0, y0) to (x1, y1)."""
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    return (f"M{x0:.1f} {y0:.1f}Q{x0 + bend:.1f} {my:.1f} {mx:.1f} {my:.1f}"
            f"T{x1:.1f} {y1:.1f}")


def stagger(i, n, s, e, width):
    """Start/end of item i when n items share the window [s, e]."""
    st = s + (e - s - width) * (i / max(1, n - 1))
    return f"{st:.3f}-{st + width:.3f}"


# --------------------------------------------------------------------------
# 1. Cell Reports Methods 2025: 3D-printed plug

def plug():
    rnd = random.Random(3)
    out = []
    wells = [(40, 200, "standard well", "f-muted"), (280, 440, "+ 3D-printed plug", "f-blue")]
    for x0, x1, name, c in wells:
        xc = (x0 + x1) / 2
        out.append(text(xc, 30, name, cls="lbl " + c, anchor="middle"))
        out.append(path(f"M{x0} 42V182Q{x0} 196 {x0 + 14} 196H{x1 - 14}Q{x1} 196 {x1} 182V42",
                        cls="f-none s-muted", stroke_width=3, stroke_linecap="round"))
        # where the cells have to end up: the entrance of the migration channel
        out.append(rect(xc - 14, 194.5, 28, 6, 3, cls="f-gold"))

    # plug: a solid insert with a tapered bore, slid in from above
    # the bore flares outward as it rises, so its walls are gently concave
    plug_shape = g(
        path("M283 46H296C300 112 330 170 350 193H297Q283 193 283 180Z",
             cls="f-blue-soft s-blue", stroke_width=1.5, stroke_linejoin="round"),
        path("M437 46H424C420 112 390 170 370 193H423Q437 193 437 180Z",
             cls="f-blue-soft s-blue", stroke_width=1.5, stroke_linejoin="round"),
        t="slide@.06-.18", dy=-170,
    )
    out.append(plug_shape)

    # 16 cells into each well
    cell_r = 4.4
    left = []
    xs = sorted(rnd.uniform(48, 192) for _ in range(16))
    # keep exactly two inside the assay region so the ratio reads 2/16 vs 16/16
    xs = [x for x in xs if not (101 <= x <= 139)][:14] + [114, 126]
    for x in xs:
        left.append((x, 191 - (rnd.random() < 0.25) * 8))
    right = []
    for y, cols in ((187, [355.5, 364.5]), (179, [351, 360, 369]), (171, [351.5, 360, 368.5]),
                    (163, [346.5, 355.5, 364.5, 373.5]), (155, [346.5, 355.5, 364.5, 373.5])):
        right += [(x, y) for x in cols]

    x0_, x1_ = (44, 300), (196, 420)   # where cells can enter each well
    for k, cells in enumerate((left, right)):
        order = list(range(len(cells)))
        rnd.shuffle(order)
        for n, i in enumerate(order):
            x, y = cells[i]
            used = (k == 1) or (101 <= x <= 139)
            win = stagger(n, 16, .2 + k * .03, .46 + k * .04, .1)
            s0, e0 = (float(v) for v in win.split("-"))
            # fall from above the well, swaying (left) or sliding down the bore (right)
            sx = rnd.uniform(x0_[k] + 12, x1_[k] - 12)
            route = drift(sx, 50, x, y, rnd.uniform(-26, 26) if k == 0 else (x - sx) * 0.15)
            out.append(circle(x, y, cell_r, cls="f-cell s-blue", stroke_width=1.4,
                              t=f"fade@{s0:.3f}-{s0 + .02:.3f} path@{s0:.3f}-{e0:.3f}", path=route))
            if used:
                out.append(circle(x, y, cell_r + 1.6, cls="f-none s-gold", stroke_width=2,
                                  t="pop@.52-.58"))

    out.append(text(120, 246, "cell usage 1×", cls="lbl", anchor="middle", font_size=17, t="rise@.6-.66"))
    out.append(g(
        rect(310, 226, 100, 28, 14, cls="f-gold"),
        text(360, 246, "8× usage", cls="lbl", anchor="middle", font_size=16, fill="#1f2430"),
        t="pop@.66-.74",
    ))
    out.append(caption(("funnel cells", "f-blue"), (" to the assay: ", "f-ink"),
                       ("8× cell usage", "f-gold-ink")))
    return svg("plug", "Animation: in a standard well only 2 of 16 loaded cells settle on the "
               "assay region; a 3D-printed plug with a tapered bore funnels all of them there, "
               "an 8-fold gain in cell usage efficiency", out)


# --------------------------------------------------------------------------
# 2. Cancer Letters 2026: screen + PGCC Explorer portal

def pgcc_portal():
    rnd = random.Random(7)
    out = []
    # plates for six cell lines, stacked
    for k in (2, 1):
        out.append(rect(26 + k * 7, 40 - k * 7, 170, 112, 7, cls="f-card",
                        t=f"rise@{.03 + (2 - k) * .02:.2f}-{.09 + (2 - k) * .02:.2f}"))
    out.append(rect(26, 40, 170, 112, 7, cls="f-card", t="rise@.07-.13"))
    for col in range(12):
        for row in range(8):
            x, y = 40 + col * 13, 54 + row * 12.3
            out.append(circle(x, y, 4.2, cls="f-line"))
            shade = rnd.random()
            c = "f-gold" if shade > 0.86 else "f-blue"
            op = 0.25 + 0.75 * rnd.random() if c == "f-blue" else 1
            out.append(circle(x, y, 4.2, cls=c, opacity=f"{op:.2f}",
                              t=f"fade@{stagger(col, 12, .12, .32, .03)}"))
    out.append(text(26, 178, "2,726 compounds", cls="big f-ink", font_size=21, t="count@.12-.34", to=2726))
    out.append(text(26, 200, "× 6 cell lines", cls="lbl", t="rise@.3-.36"))
    out.append(text(26, 222, "3 cancer types", cls="lbl f-muted", font_size=13, t="rise@.33-.39"))

    # browser window
    bx, by, bw, bh = 220, 30, 238, 222
    win = [
        rect(bx, by, bw, bh, 9, cls="f-card"),
        path(f"M{bx} {by + 22}H{bx + bw}", cls="s-line", stroke_width=1.2),
        circle(bx + 13, by + 11, 3.5, cls="f-dead"),
        circle(bx + 25, by + 11, 3.5, cls="f-gold"),
        circle(bx + 37, by + 11, 3.5, cls="f-live"),
        rect(bx + 50, by + 3, 160, 16, 8, cls="f-panel"),
        text(bx + 60, by + 15.5, "PGCC Explorer", cls="lbl f-blue", font_size=11),
    ]
    out.append(g(*win, t="rise@.36-.44"))

    # heatmap: drugs x cell lines, for non-PGCC and PGCC readouts
    hx, hy = bx + 18, by + 64
    cw, ch, gap = 15, 11.5, 22
    out.append(g(
        circle(hx + 12, hy - 25, 5, cls="f-cell s-blue", stroke_width=1.2),
        text(hx + 22, hy - 21, "non-PGCC", cls="lbl", font_size=12),
        circle(hx + 6 * cw + gap + 12, hy - 25, 9, cls="f-cell s-gold", stroke_width=1.6),
        circle(hx + 6 * cw + gap + 12, hy - 25, 4.5, cls="f-gold"),
        text(hx + 6 * cw + gap + 26, hy - 21, "PGCC", cls="lbl f-gold-ink", font_size=12),
        t="fade@.42-.47",
    ))
    cells = []
    hit_row = 6
    for row in range(10):
        for blk in range(2):
            for col in range(6):
                v = rnd.random()
                if row == hit_row:
                    v = 0.85 + 0.15 * rnd.random()
                x = hx + blk * (6 * cw + gap) + col * cw
                y = hy + row * ch
                cls = "f-blue" if blk == 0 else "f-gold"
                cells.append((x, y, cls, 0.12 + 0.88 * v ** 2))
    order = list(range(len(cells)))
    rnd.shuffle(order)
    for n, i in enumerate(order):
        x, y, cls, op = cells[i]
        out.append(rect(x + 0.8, y + 0.8, cw - 1.6, ch - 1.6, 2.5, cls=cls, opacity=f"{op:.2f}",
                        t=f"fade@{stagger(n, len(cells), .46, .7, .02)}"))
    out.append(rect(hx - 4, hy + hit_row * ch - 2, 12 * cw + gap + 8, ch + 4, 4,
                    cls="f-none s-ink", stroke_width=1.8, t="fade@.74-.78"))
    out.append(g(
        rect(bx + 80, hy + hit_row * ch + 16, 110, 22, 6, cls="f-ink"),
        text(bx + 135, hy + hit_row * ch + 31, "hits both", cls="lbl", anchor="middle",
             font_size=12, fill="var(--t-panel)"),
        t="rise@.77-.82",
    ))
    out.append(caption(("screen", "f-blue"), (" every drug, ", "f-ink"),
                       ("share", "f-gold-ink"), (" every result", "f-ink")))
    return svg("pgcc-portal", "Animation: 2,726 compounds screened across six breast, pancreatic "
               "and prostate cancer cell lines fill a heatmap of non-PGCC and PGCC responses "
               "in the PGCC Explorer web portal", out)


# --------------------------------------------------------------------------
# 3. Analytical Chemistry 2025: empirical + virtual screening

def pgcc_screen():
    rnd = random.Random(11)
    out = []
    px, py, pw, ph = 18, 26, 214, 222
    out.append(rect(px, py, pw, ph, 9, cls="f-card"))
    out.append(text(px + pw / 2, py + 22, "single-cell morphology", cls="tag", anchor="middle", font_size=11))

    def ghost(x, y, rad, t):
        return circle(x, y, rad, cls="f-none s-faint", stroke_width=1.2, stroke_dasharray="2.5 2.5", t=t)

    # field 1: a standard drug clears small cells, the PGCC survives
    # field 2: an anti-PGCC hit clears the PGCC too
    fields = [
        dict(y0=py + 32, name="standard drug", cls="tag", die=(.14, .22), giant=None,
             verdict=("PGCC persists", "f-dead", .24)),
        dict(y0=py + 126, name="anti-PGCC hit", cls="tag f-gold-ink", die=(.36, .42), giant=(.44, .52),
             verdict=("PGCC cleared", "f-live", .52)),
    ]
    gx = px + pw - 64
    for f in fields:
        y0 = f["y0"]
        st = f["die"][0] - .08
        out.append(rect(px + 10, y0, pw - 20, 88, 8, cls="f-panel", t=f"fade@{st:.2f}-{st + .04:.2f}"))
        out.append(text(px + 20, y0 + 18, f["name"], cls=f["cls"], font_size=11, t=f"fade@{st:.2f}-{st + .04:.2f}"))
        gy = y0 + 42
        small = []
        while len(small) < 7:
            x, y = rnd.uniform(px + 26, gx - 54), rnd.uniform(y0 + 32, y0 + 76)
            if all(math.dist((x, y), q) > 17 for q in small):
                small.append((x, y))
        d0, d1 = f["die"]
        for x, y in small:
            out.append(ghost(x, y, 6, f"fade@{d0 + .02:.2f}-{d1:.2f}"))
            out.append(g(circle(x, y, 6, cls="f-cell s-blue", stroke_width=1.3),
                         circle(x, y, 2.4, cls="f-blue"), t=f"fade@{st:.2f}-{st + .04:.2f} out@{d0:.2f}-{d1:.2f}"))
        live = g(circle(gx, gy, 16, cls="f-cell s-gold", stroke_width=2), circle(gx, gy, 8.5, cls="f-gold"),
                 t=f"fade@{st:.2f}-{st + .04:.2f}" + (f" out@{f['giant'][0]:.2f}-{f['giant'][1]:.2f}" if f["giant"] else ""))
        if f["giant"]:
            out.append(ghost(gx, gy, 16, f"fade@{f['giant'][0] + .02:.2f}-{f['giant'][1]:.2f}"))
        else:
            out.append(circle(gx, gy, 21, cls="f-none s-dead", stroke_width=1.8, stroke_dasharray="4 3",
                              t=f"pop@{f['verdict'][2]:.2f}-{f['verdict'][2] + .05:.2f}"))
        out.append(live)
        word, wcls, wt = f["verdict"]
        out.append(text(gx, y0 + 77, word, cls="lbl " + wcls, anchor="middle", font_size=12,
                        t=f"rise@{wt:.2f}-{wt + .05:.2f}"))

    # in silico side
    qx = 248
    out.append(text(qx, 42, "chemical fingerprint", cls="tag", font_size=11, t="fade@.56-.6"))
    bits = [1, 0, 1, 1, 0, 0, 1, 0, 1, 1, 0, 1]
    for i, b in enumerate(bits):
        out.append(rect(qx + i * 17, 50, 14, 14, 2.5, cls="f-blue" if b else "f-line",
                        t=f"pop@{stagger(i, 12, .58, .66, .03)}"))
    # small network
    # every layer centred under the fingerprint row
    mid = qx + (12 * 17 - 3) / 2
    layers = [[mid + (i - (n - 1) / 2) * 30 for i in range(n)] for n in (5, 4, 2)]
    ys = [86, 108, 128]
    for li in range(2):
        for a in layers[li]:
            for b in layers[li + 1]:
                y0, y1 = ys[li], ys[li + 1]
                h = (y1 - y0) / 2
                out.append(path(f"M{a:.1f} {y0}C{a:.1f} {y0 + h} {b:.1f} {y1 - h} {b:.1f} {y1}", cls="f-none s-line",
                                stroke_width=1, t="fade@.64-.68"))
    for li, xs_ in enumerate(layers):
        for x in xs_:
            out.append(circle(x, ys[li], 4, cls="f-blue" if li < 2 else "f-gold", t=f"pop@{.64 + li * .02:.2f}-{.68 + li * .02:.2f}"))

    out.append(text(qx, 156, "6,000+ drugs ranked", cls="tag", font_size=11, t="fade@.68-.72"))
    widths = [196, 184, 176, 165, 158, 120, 104, 88]
    for i, wdt in enumerate(widths):
        y = 164 + i * 10.5
        out.append(rect(qx, y, wdt * 0.82, 7, 3.5, cls="f-gold" if i < 5 else "f-faint",
                        t=f"grow@{stagger(i, 8, .7, .8, .04)}"))
    for i in range(5):
        y = 164 + i * 10.5
        cx_ = qx + widths[i] * 0.82 + 11
        out.append(g(circle(cx_, y + 3.5, 5, cls="f-live"),
                     path(f"M{cx_ - 2.4:.1f} {y + 3.6:.1f}l1.7 1.7l3.2 -3.4", cls="f-none", stroke="#fff",
                          stroke_width=1.5, stroke_linecap="round", stroke_linejoin="round"),
                     t=f"pop@{stagger(i, 5, .8, .86, .025)}"))
    out.append(text(qx + 186, 216, "5", cls="big f-live", anchor="middle", font_size=22, t="rise@.84-.88"))
    out.append(text(qx + 186, 234, "validated", cls="lbl f-live", anchor="middle", font_size=12, t="rise@.85-.89"))

    out.append(caption(("screen", "f-blue"), (" in the lab, ", "f-ink"),
                       ("rank", "f-gold-ink"), (" in silico", "f-ink")))
    return svg("pgcc-screen", "Animation: single-cell morphology shows a standard drug clearing "
               "small cancer cells while polyploid giant cancer cells persist, then an anti-PGCC "
               "hit clearing both; a model trained on chemical fingerprints ranks over 6,000 "
               "drugs and five top picks are validated", out)


# --------------------------------------------------------------------------
# 4. Lab on a Chip 2025 review: robotics + AI around microfluidics

def robot_ai():
    out = []
    nodes = [(84, 84, "robotic operation"), (396, 84, "single-cell imaging"),
             (396, 200, "deep learning"), (84, 200, "hypothesis")]
    # a soft closed loop through the four nodes, one cubic per side
    sides = ["M84 84C150 62 330 62 396 84", "M396 84C424 110 424 174 396 200",
             "M396 200C330 222 150 222 84 200", "M84 200C56 174 56 110 84 84"]
    loop = "M84 84C150 62 330 62 396 84C424 110 424 174 396 200C330 222 150 222 84 200C56 174 56 110 84 84Z"
    out.append(path(loop, cls="f-none s-line", stroke_width=2.5, pathLength="1", t="draw@.03-.16"))
    # direction chevrons at the middle of each side
    for (x, y, ang) in ((240, 67.5, 0), (417, 142, 90), (240, 216.5, 180), (63, 142, 270)):
        out.append(path("M-4 -5L2 0L-4 5", cls="f-none s-faint", stroke_width=2, stroke_linecap="round",
                        stroke_linejoin="round", transform=f"translate({x} {y}) rotate({ang})"))

    # chip in the middle with a serpentine channel and passing cells
    cx, cy = 240, 141
    chan = "M186 128H294C305 128 305 141 294 141H186C175 141 175 154 186 154H294"
    out.append(g(
        rect(cx - 64, cy - 32, 128, 64, 12, cls="f-card"),
        path(chan, cls="f-none s-blue", stroke_width=6, stroke_linecap="round", opacity=".16"),
        path(chan, cls="f-none s-blue", stroke_width=1.4, stroke_linecap="round"),
        circle(186, 128, 4, cls="f-blue"), circle(294, 154, 4, cls="f-blue"),
        t="pop@.06-.14",
    ))
    for k in range(3):
        st = .14 + k * .1
        out.append(circle(294, 154, 3.2, cls="f-gold",
                          t=f"fade@{st:.2f}-{st + .02:.2f} path@{st:.2f}-{st + .4:.2f}", path=chan))

    icons = [
        # robot arm
        g(path("M-11 12H11", stroke_width=3), path("M-5 12V7C-5 3 -4 0 -2 -3L6 -9", stroke_width=2.6),
          circle(-2, -3, 2.2), path("M6 -9Q10 -8 11 -4M6 -9Q8 -12 11 -13", stroke_width=2.2)),
        # microscope
        g(path("M-11 13H11", stroke_width=3), path("M-4 13V9M-6 -12L3 -2", stroke_width=2.6),
          path("M3 -2L-1 2", stroke_width=4), path("M6 13C12 8 11 -2 4 -5", stroke_width=2)),
        # network
        g(circle(-9, -8, 3), circle(-9, 8, 3), circle(9, 0, 3),
          path("M-6 -7C0 -7 0 -1 6 -1M-6 7C0 7 0 1 6 1", stroke_width=1.8)),
        # bulb
        g(path("M-6 4C-12 -4 -7 -13 0 -13C7 -13 12 -4 6 4V8H-6Z", stroke_width=2.2),
          path("M-4 12H4", stroke_width=2.2)),
    ]
    for i, ((x, y, name), ic) in enumerate(zip(nodes, icons)):
        arrive = .2 + i * .17
        out.append(circle(x, y, 25, cls="f-card", t=f"pop@{.08 + i * .02:.2f}-{.14 + i * .02:.2f}"))
        out.append(circle(x, y, 25, cls="f-gold-soft s-gold", stroke_width=2,
                          t=f"pop@{arrive:.2f}-{arrive + .05:.2f}"))
        out.append(g(ic, transform=f"translate({x} {y})", cls="s-ink f-none",
                     stroke_linecap="round", stroke_linejoin="round"))
        ly = y - 34 if y < 140 else y + 42
        out.append(text(x, ly, name, cls="lbl", anchor="middle", font_size=13,
                        t=f"fade@{.1 + i * .02:.2f}-{.15 + i * .02:.2f}"))

    # a pulse travels each side in turn, lighting the next node as it lands
    for i, d in enumerate(sides):
        st = .2 + i * .17
        ex, ey = nodes[(i + 1) % 4][:2]
        out.append(circle(ex, ey, 6, cls="f-gold", cls_=None,
                          t=f"fade@{st - .01:.2f}-{st + .01:.2f} path@{st:.2f}-{st + .14:.2f} out@{st + .14:.2f}-{st + .17:.2f}",
                          path=d))
    out.append(g(
        path("M222 40C214 40 210 34 213 28C214 21 222 18 228 21C231 14 243 12 249 19C256 16 266 22 263 30"
             "C270 32 270 40 262 40Z", cls="f-blue-soft s-blue", stroke_width=1.6, stroke_linejoin="round"),
        text(240, 57, "shared cloud lab", cls="lbl f-blue", anchor="middle", font_size=12),
        t="rise@.84-.9",
    ))
    out.append(caption(("robots", "f-blue"), (" run it, ", "f-ink"), ("AI", "f-gold-ink"), (" reads it", "f-ink")))
    return svg("robot-ai", "Animation: around a microfluidic chip, a loop links robotic "
               "operation, single-cell imaging, deep learning and hypothesis generation, "
               "converging on a shared cloud lab", out)


# --------------------------------------------------------------------------
# 5. Lab on a Chip 2024: label-free spheroid viability

def spheroid():
    rnd = random.Random(5)
    out = []
    # chip with a microwell array
    out.append(rect(20, 36, 150, 120, 9, cls="f-card", t="rise@.03-.09"))
    pick = (3, 2)
    for i in range(6):
        for j in range(5):
            x, y = 38 + i * 23, 54 + j * 21
            out.append(circle(x, y, 8, cls="f-panel s-line", stroke_width=1))
            out.append(circle(x + rnd.uniform(-1.5, 1.5), y + rnd.uniform(-1.5, 1.5), 4.6, cls="f-muted",
                              opacity=".55", t=f"pop@{stagger(i * 5 + j, 30, .06, .2, .04)}"))
    sx, sy = 38 + pick[0] * 23, 54 + pick[1] * 21
    out.append(circle(sx, sy, 10, cls="f-none s-gold", stroke_width=2, t="pop@.2-.24"))
    out.append(text(20, 178, "~12,000 spheroids", cls="big f-ink", font_size=18, t="count@.06-.22", to=12000))
    out.append(text(20, 196, "per chip, label-free", cls="lbl", font_size=13, t="rise@.18-.24"))

    # zoomed phase-contrast spheroid
    zx, zy = 248, 108
    out.append(path(f"M{sx + 10} {sy - 5}C{sx + 40} {sy - 30} {zx - 80} {zy - 52} {zx - 48} {zy - 36}"
                    f"M{sx + 10} {sy + 5}C{sx + 40} {sy + 26} {zx - 80} {zy + 50} {zx - 48} {zy + 36}",
                    cls="f-none s-faint", stroke_width=1, stroke_dasharray="3 3", t="fade@.22-.26"))
    out.append(circle(zx, zy, 56, cls="f-card", t="pop@.22-.28"))
    edge = blob(zx, zy, 40, 1.6, 14, rnd)
    healthy = [path(edge, cls="f-faint"), path(edge, cls="f-none s-muted", stroke_width=2.2)]
    for _ in range(26):
        a, d = rnd.uniform(0, 6.283), 34 * math.sqrt(rnd.random())
        healthy.append(circle(zx + d * math.cos(a), zy + d * math.sin(a), rnd.uniform(1.6, 3), cls="f-muted", opacity=".5"))
    out.append(g(*healthy, t="pop@.24-.3 out@.42-.52"))
    # treated: smaller, ragged edge, shed debris
    # treated: smaller, with a frayed but still rounded edge
    dying = [path(blob(zx, zy, 32, 4.5, 18, rnd), cls="f-faint s-muted", stroke_width=1.6, opacity=".85")]
    for _ in range(14):
        a, d = rnd.uniform(0, 6.283), rnd.uniform(38, 50)
        dying.append(circle(zx + d * math.cos(a), zy + d * math.sin(a), rnd.uniform(1.2, 2.4), cls="f-muted", opacity=".6"))
    out.append(g(*dying, t="fade@.44-.54"))
    out.append(g(path(f"M{zx} 26C{zx - 6} 34 {zx - 7} 40 {zx} 42C{zx + 7} 40 {zx + 6} 34 {zx} 26Z", cls="f-gold"),
                 text(zx + 12, 40, "drug", cls="lbl f-gold-ink", font_size=12),
                 t="slide@.34-.4 out@.46-.5", dy=-30, cls="t-gone"))
    out.append(text(zx, zy + 72, "phase contrast", cls="lbl", anchor="middle", font_size=12, t="fade@.26-.3"))

    # CNN
    nx = 322
    for k, (hgt, wid) in enumerate(((64, 10), (48, 10), (32, 10))):
        out.append(rect(nx + k * 16, zy - hgt / 2, wid, hgt, 2.5, cls="f-blue", opacity=f"{.45 + k * .2:.2f}",
                        t=f"pop@{.3 + k * .03:.2f}-{.35 + k * .03:.2f}"))
    out.append(text(nx + 21, zy + 50, "CNN", cls="lbl f-blue", anchor="middle", font_size=12, t="fade@.36-.4"))
    # viability gauge: fill drops as the spheroid dies
    gx, gy, gh = 400, 54, 108
    out.append(rect(gx, gy, 22, gh, 6, cls="f-line", t="fade@.36-.4"))
    out.append(tag("clipPath", rect(gx, gy, 22, gh, 6), id="t-sph-clip"))
    out.append(g(
        rect(gx, gy, 22, gh, 0, cls="f-live", t="fade@.38-.42"),
        rect(gx, gy - gh, 22, gh, 0, cls="f-line", t="move@.48-.6", my=str(int(gh * 0.62))),
        clip_path="url(#t-sph-clip)",
    ))
    out.append(text(gx + 11, gy + gh + 18, "viability", cls="lbl", anchor="middle", font_size=12, t="fade@.38-.42"))

    # viability over time, tracked through treatment
    cx0, cy0, cwid = 196, 196, 254
    out.append(path(f"M{cx0} {cy0}V{cy0 + 50}H{cx0 + cwid}", cls="f-none s-faint", stroke_width=1.2, t="fade@.58-.62"))
    curve = (f"M{cx0 + 4} {cy0 + 8}H{cx0 + 80}C{cx0 + 120} {cy0 + 8} {cx0 + 130} {cy0 + 40} "
             f"{cx0 + 170} {cy0 + 42}H{cx0 + cwid - 4}")
    out.append(path(curve, cls="f-none s-live", stroke_width=2.6, stroke_linecap="round",
                    pathLength="1", t="draw@.6-.8"))
    out.append(path(f"M{cx0 + 80} {cy0 - 2}V{cy0 + 50}", cls="s-gold", stroke_width=1.5,
                    stroke_dasharray="3 3", t="fade@.62-.66"))
    out.append(text(cx0 + 84, cy0 + 4, "drug", cls="lbl f-gold-ink", font_size=11, t="fade@.62-.66"))
    out.append(g(rect(16, 212, 172, 28, 14, cls="f-live-soft"),
                 text(102, 231, "✓ matches LIVE/DEAD", cls="lbl f-live", anchor="middle", font_size=12),
                 t="pop@.8-.86"))
    out.append(caption(("viability", "f-blue"), (" from phase contrast, ", "f-ink"), ("no stain", "f-gold-ink")))
    return svg("spheroid", "Animation: a microfluidic chip holding about 12,000 spheroids; one "
               "spheroid's phase-contrast image shrinks and frays under drug, a convolutional "
               "network reads its viability without staining, tracked over time and matching "
               "LIVE/DEAD staining", out)


# --------------------------------------------------------------------------
# 6. Biosensors 2024: gradient generator + 3D co-culture in dECM

def cgg():
    out = []
    # Christmas-tree gradient generator: each level adds one channel; the
    # verticals are serpentine mixers, the horizontals split the flow again.
    off = -16
    levels = [[150, 330], [120, 240, 360], [105, 195, 285, 375], [90, 165, 240, 315, 390]]
    levels = [[x + off for x in lv] for lv in levels]
    tops = [44, 70, 104, 138]
    bots = [70, 104, 138, 184]
    out.append(g(circle(150 + off, 34, 9, cls="f-gold"),
                 text(134 + off, 38, "drug", cls="lbl f-gold-ink", anchor="end", font_size=13),
                 t="pop@.04-.09"))
    out.append(g(circle(330 + off, 34, 9, cls="f-card"),
                 text(346 + off, 38, "medium", cls="lbl", font_size=13),
                 t="pop@.05-.1"))

    def mixer(x, y0, y1):
        """A smooth serpentine: a wave of rounded turns between straight leads."""
        mid0, mid1 = y0 + 6, y1 - 6
        n = max(2, 2 * int((mid1 - mid0) // 9))
        step = (mid1 - mid0) / n
        d = f"M{x} {y0}V{mid0}Q{x + 7} {mid0 + step / 2:.1f} {x} {mid0 + step:.1f}"
        d += "".join(f"T{x} {mid0 + step * (k + 1):.1f}" for k in range(1, n))
        return d + f"V{y1}"

    for li, xs_ in enumerate(levels):
        st = .1 + li * .08
        n = len(xs_)
        for i, x in enumerate(xs_):
            d = mixer(x, tops[li], bots[li])
            out.append(path(d, cls="f-none s-muted", stroke_width=2, stroke_linejoin="round",
                            pathLength="1", t=f"draw@{st:.2f}-{st + .06:.2f}"))
            c = 1 - i / (n - 1)
            if c > 0:
                out.append(path(d, cls="f-none s-gold", stroke_width=3.2, stroke_linejoin="round",
                                opacity=f"{c:.2f}", pathLength="1",
                                t=f"draw@{st + .03:.2f}-{st + .1:.2f}"))
        if li + 1 < len(levels):
            nxt = levels[li + 1]
            y = bots[li]
            out.append(path(f"M{nxt[0]} {y + 6}Q{nxt[0]} {y} {nxt[0] + 6} {y}H{nxt[-1] - 6}Q{nxt[-1]} {y} {nxt[-1]} {y + 6}",
                            cls="f-none s-muted", stroke_width=2, stroke_linecap="round", pathLength="1",
                            t=f"draw@{st + .05:.2f}-{st + .09:.2f}"))

    # culture chambers, one per dose
    outs = levels[-1]
    for i, x in enumerate(outs):
        c = 1 - i / (len(outs) - 1)
        bx, by = x - 28, 186
        ch = [rect(bx, by, 56, 52, 9, cls="f-card")]
        ch.append(rect(bx, by, 56, 52, 9, cls="f-gold", opacity=f"{.06 + .34 * c:.2f}", t="fade@.5-.58"))
        ch.append(path(f"M{bx + 6} {by + 40}C{bx + 16} {by + 30} {bx + 26} {by + 46} {bx + 36} {by + 38}S{bx + 46} {by + 30} {bx + 50} {by + 34}",
                       cls="f-none s-blue", stroke_width=4.5, stroke_linecap="round", opacity=".55",
                       t="draw@.58-.68", pathLength="1"))
        for (ox, oy) in ((0, 0), (-6, -3), (6, -3), (0, -8), (-5, 5), (5, 5)):
            ch.append(circle(bx + 28 + ox, by + 18 + oy, 3.6, cls="f-gold-ink", opacity=".85",
                             t=f"pop@{.6 + i * .012:.3f}-{.66 + i * .012:.3f}"))
        out.append(g(*ch, t=f"rise@{.44 + i * .015:.3f}-{.5 + i * .015:.3f}"))
    out.append(text(outs[0], 252, "high dose", cls="lbl f-gold-ink", anchor="middle", font_size=11, t="fade@.7-.74"))
    out.append(text(outs[-1], 252, "low dose", cls="lbl", anchor="middle", font_size=11, t="fade@.7-.74"))
    out.append(g(
        circle(408, 196, 3.6, cls="f-gold-ink"), text(415, 200, "SY5Y", cls="lbl f-gold-ink", font_size=11),
        path("M403 212H412", cls="s-blue", stroke_width=4, stroke_linecap="round", opacity=".55"),
        text(415, 216, "HBMVEC", cls="lbl f-blue", font_size=11),
        rect(403, 225, 10, 9, 2, cls="f-gold", opacity=".25"), text(415, 233, "dECM gel", cls="lbl", font_size=11),
        t="fade@.7-.76",
    ))
    out.append(caption(("one chip", "f-blue"), (", a full ", "f-ink"), ("dose gradient", "f-gold-ink")))
    return svg("cgg", "Animation: a concentration gradient generator splits drug and medium "
               "into five graded doses, each feeding a 3D chamber of neuroblastoma (SY5Y) cells "
               "and brain microvascular endothelial cells in decellularized ECM hydrogel", out)


# --------------------------------------------------------------------------
# 7. ACS Nano 2024: NIR neural dye, vesicle to brain

def neuron_tree(sx, sy, soma_r, prims, rnd, depth=2):
    """Dendrites that only ever branch outward from a parent's tip.

    prims: (angle in degrees, length, width) per primary process. Each level
    splits in two at a narrowing angle, so siblings fan apart and nothing
    doubles back across another branch. Returns [(d, width, level, tip)].
    """
    segs = []

    def grow(x, y, ang, length, width, level):
        a = math.radians(ang)
        ex, ey = x + length * math.cos(a), y + length * math.sin(a)
        bend = rnd.uniform(-0.12, 0.12) * length
        cx = (x + ex) / 2 - math.sin(a) * bend
        cy = (y + ey) / 2 + math.cos(a) * bend
        segs.append((f"M{x:.1f} {y:.1f}Q{cx:.1f} {cy:.1f} {ex:.1f} {ey:.1f}", width, level, (ex, ey)))
        if level < depth:
            spread = (19, 13)[min(level, 1)]
            for side in (-1, 1):
                grow(ex, ey, ang + side * spread + rnd.uniform(-4, 4),
                     length * rnd.uniform(.55, .68), width * .66, level + 1)

    for ang, length, width in prims:
        a = math.radians(ang)
        grow(sx + soma_r * .9 * math.cos(a), sy + soma_r * .9 * math.sin(a), ang, length, width, 0)
    return segs


def nir_dye():
    rnd = random.Random(21)
    out = []
    out.append(rect(18, 26, 246, 222, 10, cls="f-card"))
    sx, sy, sr = 112, 134, 14
    # five dendrites, kept clear of the badge (top right) and the label (bottom right)
    segs = neuron_tree(sx, sy, sr, [(-96, 40, 3.4), (-148, 36, 3.2), (166, 36, 3.2),
                                    (118, 38, 3.2), (66, 32, 3)], rnd)
    # axon: one long gentle wave out to the right, then a terminal fan
    ax0, ay0 = sx + sr - 1, sy + 2
    axon = f"M{ax0} {ay0}C{ax0 + 40} {ay0 - 12} {ax0 + 70} {ay0 + 12} {ax0 + 108} {ay0 + 2}"
    tip = (ax0 + 108, ay0 + 2)
    segs.append((axon, 2.8, 0, tip))
    for ang in (-34, 0, 34):
        a = math.radians(ang)
        ex, ey = tip[0] + 22 * math.cos(a), tip[1] + 22 * math.sin(a)
        segs.append((f"M{tip[0]:.1f} {tip[1]:.1f}Q{tip[0] + 12 * math.cos(a * .5):.1f} {tip[1] + 12 * math.sin(a * .5):.1f} "
                     f"{ex:.1f} {ey:.1f}", 1.8, 1, (ex, ey)))
        out.append(circle(ex, ey, 2.4, cls="f-faint"))   # synaptic boutons

    soma = blob(sx, sy, sr, 1.2, 8, rnd)
    base = [path(d, cls="f-none s-faint", stroke_width=w, stroke_linecap="round") for d, w, _, _ in segs]
    base.append(path(soma, cls="f-cell s-faint", stroke_width=2.4))
    out.append(g(*base, t="fade@.03-.08"))

    # dye molecules drift in on curves and land on the membrane
    lands = [(sx + sr * math.cos(a), sy + sr * math.sin(a)) for a in [k * 0.63 for k in range(10)]]
    lands += [t for _, _, lvl, t in segs if lvl >= 1][:16]
    for k, (tx, ty_) in enumerate(lands):
        win = stagger(k, len(lands), .08, .26, .1)
        s0, e0 = (float(v) for v in win.split("-"))
        fx, fy = tx + rnd.uniform(-70, 70), ty_ + rnd.uniform(-60, 60)
        out.append(circle(tx, ty_, 2.4, cls="f-nir",
                          t=f"fade@{s0:.3f}-{s0 + .03:.3f} path@{s0:.3f}-{e0:.3f} out@.34-.4",
                          path=drift(fx, fy, tx, ty_, rnd.uniform(-30, 30))))

    # the stain spreads from the soma outward, one branch order at a time
    glow = []
    for d, w, lvl, _ in segs:
        st = .3 + lvl * .05
        glow.append(path(d, cls="f-none s-nir", stroke_width=w, stroke_linecap="round", pathLength="1",
                         t=f"draw@{st:.2f}-{st + .07:.2f}"))
    glow.append(path(soma, cls="f-card", t="pop@.27-.32"))
    glow.append(path(soma, cls="f-nir-soft s-nir", stroke_width=2.6, t="pop@.27-.32"))
    out.append(g(*glow))
    out.append(g(rect(176, 38, 76, 26, 13, cls="f-nir"),
                 text(214, 56, "< 1 min", cls="lbl", anchor="middle", font_size=14, fill="#fff"),
                 t="pop@.34-.4"))
    out.append(text(252, 238, "NIR emission > 700 nm", cls="lbl f-nir", anchor="end", font_size=12, t="fade@.4-.46"))

    # multiscale tiles, labels top right, drawings low and left
    tiles = [("vesicles", .5), ("single neuron", .6), ("whole brain", .7)]
    for i, (name, st) in enumerate(tiles):
        ty = 26 + i * 76
        tile = [rect(280, ty, 180, 68, 10, cls="f-card")]
        if i == 0:
            neurite = f"M290 {ty + 46}C320 {ty + 34} 352 {ty + 56} 384 {ty + 44}S420 {ty + 36} 440 {ty + 46}"
            tile.append(path(neurite, cls="f-none s-faint", stroke_width=4, stroke_linecap="round"))
            def bez(p0, p1, p2, p3, u):
                return tuple((1 - u) ** 3 * a + 3 * (1 - u) ** 2 * u * b + 3 * (1 - u) * u * u * c + u ** 3 * d
                             for a, b, c, d in zip(p0, p1, p2, p3))
            halves = [((290, ty + 46), (320, ty + 34), (352, ty + 56), (384, ty + 44)),
                      ((384, ty + 44), (416, ty + 32), (420, ty + 36), (440, ty + 46))]
            for k in range(8):
                h = halves[k // 4]
                x, y = bez(*h, (k % 4 + .5) / 4)
                tile.append(circle(x, y, 3, cls="f-nir"))
        elif i == 1:
            mini = neuron_tree(312, ty + 40, 6, [(-105, 11, 1.8), (-165, 11, 1.8), (150, 10, 1.8), (100, 9, 1.8)],
                               random.Random(4), depth=1)
            for d, w, _, _ in mini:
                tile.append(path(d, cls="f-none s-nir", stroke_width=w, stroke_linecap="round"))
            tile.append(path(f"M318 {ty + 41}C340 {ty + 36} 360 {ty + 46} 392 {ty + 40}", cls="f-none s-nir",
                             stroke_width=1.6, stroke_linecap="round"))
            tile.append(path(blob(312, ty + 40, 6, .5, 7, random.Random(5)), cls="f-nir-soft s-nir", stroke_width=1.8))
        else:
            # mouse brain, lateral view: bulb, cortex, cerebellum, brainstem
            # long and low, as the mouse brain is; drawn back to front so each
            # part tucks under the one in front of it
            ox, oy = 296, ty + 20
            tile.append(path(f"M{ox + 56} {oy + 22}C{ox + 66} {oy + 30} {ox + 78} {oy + 33} {ox + 90} {oy + 32}"
                             f"Q{ox + 96} {oy + 33} {ox + 92} {oy + 38}C{ox + 78} {oy + 40} {ox + 64} {oy + 36} {ox + 54} {oy + 28}Z",
                             cls="f-nir-soft s-nir", stroke_width=1.4, stroke_linejoin="round"))
            tile.append(path(blob(ox + 76, oy + 21, 11, .4, 10, random.Random(8), squash=.86),
                             cls="f-card s-nir", stroke_width=1.6))
            tile.append(path(blob(ox + 76, oy + 21, 11, .4, 10, random.Random(8), squash=.86), cls="f-nir-soft"))
            for k in range(4):
                y = oy + 14 + k * 4.6
                half = 9 - abs(k - 1.5) * 1.6
                tile.append(path(f"M{ox + 76 - half:.1f} {y + 1:.1f}Q{ox + 76:.1f} {y - 2:.1f} {ox + 76 + half:.1f} {y + 1:.1f}",
                                 cls="f-none s-nir", stroke_width=.9, opacity=".6"))
            tile.append(tag("ellipse", cx=ox + 6, cy=oy + 18, rx=7, ry=5, cls="f-nir-soft s-nir", stroke_width=1.5,
                            transform=f"rotate(-10 {ox + 6} {oy + 18})"))
            cortex = smooth_closed([(ox + 11, oy + 19), (ox + 18, oy + 8), (ox + 36, oy + 1), (ox + 56, oy + 2),
                                    (ox + 69, oy + 10), (ox + 69, oy + 22), (ox + 46, oy + 27), (ox + 22, oy + 26)])
            tile.append(path(cortex, cls="f-card s-nir", stroke_width=1.8))
            tile.append(path(cortex, cls="f-nir-soft"))
            # rhinal fissure along the lower cortex
            tile.append(path(f"M{ox + 17} {oy + 22}Q{ox + 42} {oy + 18} {ox + 66} {oy + 20}", cls="f-none s-nir",
                             stroke_width=1, opacity=".5"))
        tile.append(text(452, ty + 20, name, cls="lbl", anchor="end", font_size=12))
        out.append(g(*tile, t=f"slide@{st:.2f}-{st + .07:.2f}", dx=24))
    out.append(caption(("stain in < 1 min", "f-nir"), (", image ", "f-ink"), ("vesicle → brain", "f-blue")))
    return svg("nir-dye", "Animation: near-infrared dye molecules land on a neuron's membrane and "
               "light it up in under a minute, with emission above 700 nm, then the same dye "
               "images vesicles, a single neuron and a whole brain", out)


# --------------------------------------------------------------------------
# 8. Nano Letters 2022: inhaled nanoplastics reach the brain

def nanoplastic():
    rnd = random.Random(13)
    out = []
    # the head fades out towards the neck instead of ending on a hard edge
    out.append(tag("defs", [
        tag("linearGradient", [tag("stop", offset="0", stop_color="#fff"), tag("stop", offset=".8", stop_color="#fff"),
                               tag("stop", offset="1", stop_color="#fff", stop_opacity="0")],
            id="t-np-fade", x1="0", y1="0", x2="0", y2="1"),
        tag("mask", rect(0, 0, 270, 250, fill="url(#t-np-fade)"), id="t-np-mask"),
    ]))
    head = ("M50 154C52 142 64 128 84 118C112 104 150 98 184 102C222 106 248 128 254 160"
            "C258 186 256 212 252 240L150 240C120 222 92 200 72 182C58 170 49 164 50 154Z")
    out.append(g(
        path(head, cls="f-card"),
        # the ear sits in front of the head, overlapping its crown
        g(tag("ellipse", cx=0, cy=0, rx=19, ry=24, cls="f-card"),
          tag("ellipse", cx=0, cy=2, rx=11, ry=15, cls="f-dead-soft"),
          transform="translate(196 90) rotate(14)"),
        path("M100 118C108 112 118 110 126 112", cls="f-none s-line", stroke_width=1.5, stroke_linecap="round"),
        mask="url(#t-np-mask)", t="fade@.02-.08",
    ))
    out.append(circle(108, 138, 3.8, cls="f-ink"))
    out.append(circle(52, 153, 4.5, cls="f-dead", opacity=".75"))
    out.append(g(*[path(f"M66 {156 + k * 5}Q46 {150 + k * 9} 26 {146 + k * 14}", cls="f-none s-faint",
                        stroke_width=1.1, stroke_linecap="round") for k in range(3)]))
    brain = path(blob(178, 152, 38, 1.5, 12, rnd, squash=.66), cls="f-blue-soft s-blue", stroke_width=1.5)
    out.append(g(brain,
                 path("M180 126C174 138 186 150 178 160S182 174 180 178", cls="f-none s-blue", stroke_width=1,
                      opacity=".5", stroke_linecap="round"),
                 text(180, 202, "brain", cls="lbl f-blue", anchor="middle", font_size=12), t="fade@.06-.12"))
    nasal = "M56 154C86 160 116 156 146 148"
    out.append(path(nasal, cls="f-none s-faint", stroke_width=2, stroke_dasharray="2 4", stroke_linecap="round",
                    t="fade@.12-.16"))
    # aerosol drifts to the nose, follows the nasal route and settles in the brain
    for k in range(18):
        fx, fy = 162 + rnd.uniform(-14, 30), 152 + rnd.uniform(-16, 16)
        sx_, sy_ = rnd.uniform(14, 40), rnd.uniform(110, 196)
        st = .14 + k * .013
        route = (f"M{sx_:.1f} {sy_:.1f}C{sx_ + 18:.1f} {sy_:.1f} {40} {153} {56} {154}"
                 f"C86 160 116 156 146 148C154 146 {fx - 8:.1f} {fy:.1f} {fx:.1f} {fy:.1f}")
        out.append(circle(fx, fy, 2.6, cls="f-gold-ink",
                          t=f"fade@{st:.3f}-{st + .03:.3f} path@{st:.3f}-{st + .3:.3f}", path=route))
    out.append(text(24, 52, "80 nm PS-NPs", cls="big f-gold-ink", font_size=21, t="rise@.1-.16"))
    out.append(text(24, 72, "inhaled as aerosol", cls="lbl", font_size=13, t="rise@.12-.18"))

    # right: microfluidic uptake test + outcomes
    px = 272
    out.append(rect(px, 26, 188, 136, 10, cls="f-card", t="rise@.5-.56"))
    out.append(text(px + 12, 46, "neurons on chip", cls="tag", font_size=11, t="fade@.52-.56"))
    for j, (name, rad, n) in enumerate((("smaller", 1.6, 16), ("larger", 3.6, 4))):
        cx_, cy_ = px + 50 + j * 92, 102
        st = .54 + j * .02
        neur = [path(f"M{cx_ + 13 * math.cos(a):.1f} {cy_ + 13 * math.sin(a):.1f}"
                     f"Q{cx_ + 24 * math.cos(a + .25):.1f} {cy_ + 22 * math.sin(a + .25):.1f} "
                     f"{cx_ + 32 * math.cos(a + .1):.1f} {cy_ + 27 * math.sin(a + .1):.1f}",
                     cls="f-none s-blue", stroke_width=2, stroke_linecap="round", opacity=".7")
                for a in (0.3, 1.5, 2.6, 3.7, 5.0)]
        neur.append(path(blob(cx_, cy_, 20, 1.2, 9, rnd), cls="f-cell s-blue", stroke_width=1.6))
        neur.append(circle(cx_, cy_, 8, cls="f-blue", opacity=".3"))
        out.append(g(*neur, t=f"pop@{st:.2f}-{st + .06:.2f}"))
        for k in range(n):
            a, d = rnd.uniform(0, 6.283), rnd.uniform(10, 16)
            out.append(circle(cx_ + d * math.cos(a), cy_ + d * math.sin(a), rad, cls="f-gold-ink",
                              t=f"pop@{stagger(k, n, .6, .72, .03)}"))
        out.append(text(cx_, 152, name, cls="lbl", anchor="middle", font_size=12, t="fade@.58-.62"))
    out.append(text(px + 94, 64, "smaller → more uptake", cls="lbl f-ink", anchor="middle", font_size=12, t="fade@.72-.76"))
    outcomes = [("fewer activities", .78), ("AChE activity ↓", .83)]
    for i, (s_, st) in enumerate(outcomes):
        y = 176 + i * 32
        out.append(g(rect(px, y, 188, 26, 13, cls="f-dead-soft"),
                     text(px + 94, y + 17, s_, cls="lbl f-dead", anchor="middle", font_size=13),
                     t=f"rise@{st:.2f}-{st + .05:.2f}"))
    out.append(caption(("inhaled", "f-ink"), (" nanoplastics", "f-gold-ink"), (" reach the brain", "f-blue")))
    return svg("nanoplastic", "Animation: 80 nm polystyrene nanoplastics inhaled through a "
               "mouse's nose deposit in its brain; on a microfluidic chip smaller particles are "
               "taken up more by neurons; exposed mice are less active and show inhibited AChE "
               "activity", out)


SCENES = {
    "plug": plug,
    "pgcc-portal": pgcc_portal,
    "pgcc-screen": pgcc_screen,
    "robot-ai": robot_ai,
    "spheroid": spheroid,
    "cgg": cgg,
    "nir-dye": nir_dye,
    "nanoplastic": nanoplastic,
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for key, fn in SCENES.items():
        markup = fn()
        (OUT / f"{key}.html").write_text(
            "<!-- generated by _teasers/build_teasers.py; edit that, not this -->\n" + markup + "\n",
            encoding="utf-8", newline="\n")
        print(f"{key}: {len(markup) / 1024:.1f} KB")


if __name__ == "__main__":
    main()
