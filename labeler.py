import math
import os
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_CANDIDATES = [
    os.path.join(HERE, "fonts", "Roboto-Regular.ttf"),
    "Roboto-Regular.ttf", "DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "C:/Windows/Fonts/arial.ttf",
]


@lru_cache(maxsize=64)
def get_font(px):
    px = max(6, int(px))
    for name in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(name, px)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=px)
    except TypeError:
        return ImageFont.load_default()


def sample_bg(img, n=40):
    w, h = img.size
    n = min(n, w // 2, h // 2)
    vals = []
    for box in ((0, 0, n, n), (w - n, 0, w, n), (0, h - n, n, h), (w - n, h - n, w, h)):
        vals.append(img.crop(box).resize((1, 1), Image.Resampling.BOX).getpixel((0, 0)))
    return "#%02x%02x%02x" % tuple(sum(v[i] for v in vals) // 4 for i in range(3))


def wrap_text(d, text, font, maxw):
    lines = []
    for part in text.split("|"):
        cur = ""
        for word in part.split():
            trial = (cur + " " + word).strip()
            if cur and d.textlength(trial, font=font) > maxw:
                lines.append(cur)
                cur = word
            else:
                cur = trial
        lines.append(cur)
    return [l for l in lines if l] or [""]


def _layout(d, font, fpx, lbl, k, Wpx, Hpx, pl, pt, total_w, style,
            clamp=True, maxw_override=None):
    pad, m = fpx * 0.35, fpx * 0.3
    ax, ay = (lbl["ax"] + pl) * k, (lbl["ay"] + pt) * k
    tx, ty = (lbl["tx"] + pl) * k, (lbl["ty"] + pt) * k
    right = tx >= ax
    maxw = style["wrap_pct"] / 100 * total_w * k if maxw_override is None else maxw_override
    if clamp:
        maxw = min(maxw, (Wpx - tx if right else tx) - 2 * pad - m)
    maxw = max(maxw, fpx * 3)
    lines = wrap_text(d, lbl["text"], font, maxw)
    tw = max(d.textlength(t, font=font) for t in lines)
    x_end = tx + tw + 2 * pad if right else tx - tw - 2 * pad
    lh = fpx * 1.2
    top = ty - fpx * 0.28 - (len(lines) - 1) * lh - fpx * 0.8
    if clamp:
        if right and x_end > Wpx - m:
            tx -= x_end - (Wpx - m); x_end = Wpx - m
        if not right and x_end < m:
            tx += m - x_end; x_end = m
        if top < m:
            ty += m - top
        ty = min(ty, Hpx - m)
    text_x = tx + pad if right else x_end + pad
    return dict(ax=ax, ay=ay, tx=tx, ty=ty, x_end=x_end, text_x=text_x,
                lines=lines, lh=lh, top=top)


def render(image, labels, style, scale=1.0, ss=2):
    """Zwraca gotowy obraz RGB (z marginesami i opisami) w zadanej skali."""
    pl, pt, pr, pb = style["pads"]
    tw, th = image.width + pl + pr, image.height + pt + pb
    base = Image.new("RGB", (tw, th), style["bg"])
    base.paste(image, (pl, pt))
    W, H = int(tw * scale), int(th * scale)
    if (W, H) != (tw, th):
        base = base.resize((W, H), Image.Resampling.LANCZOS)

    k = scale * ss
    ov = Image.new("RGBA", (W * ss, H * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    fpx = style["font_size"] * k
    font = get_font(fpx)
    lw = max(1, round(style["line_w"] * k))
    col = style["color"]
    dot_r = max(2.0, lw * 1.9)
    halo = max(1, round(fpx * 0.12))

    for l in labels:
        g = _layout(d, font, fpx, l, k, W * ss, H * ss, pl, pt, tw, style)
        ax, ay, tx, ty, xe = g["ax"], g["ay"], g["tx"], g["ty"], g["x_end"]
        d.line([(ax, ay), (tx, ty), (xe, ty)], fill=col, width=lw, joint="curve")
        r = lw / 2
        for (x, y) in ((tx, ty), (xe, ty)):
            d.ellipse([x - r, y - r, x + r, y + r], fill=col)
        ro = dot_r + lw * 0.8
        d.ellipse([ax - ro, ay - ro, ax + ro, ay + ro], fill=(255, 255, 255, 230))
        d.ellipse([ax - dot_r, ay - dot_r, ax + dot_r, ay + dot_r], fill=col)
        n = len(g["lines"])
        for i, line in enumerate(g["lines"]):
            y = ty - fpx * 0.28 - (n - 1 - i) * g["lh"]
            d.text((g["text_x"], y), line, font=font, fill=col, anchor="ls",
                   stroke_width=halo, stroke_fill=(255, 255, 255, 200))
            d.text((g["text_x"], y), line, font=font, fill=col, anchor="ls")
    if ss > 1:
        ov = ov.resize((W, H), Image.Resampling.LANCZOS)
    return Image.alpha_composite(base.convert("RGBA"), ov).convert("RGB")


def autofit_pads(image, labels, style):
    """Marginesy (l, t, r, b), przy których wszystkie opisy mieszczą się w całości."""
    if not labels:
        return style["pads"]
    fpx = style["font_size"]
    font = get_font(fpx)
    d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    pl, pt, pr, pb = style["pads"]
    total_w = image.width + pl + pr
    maxw = style["wrap_pct"] / 100 * total_w
    minx = miny = 0
    maxx, maxy = image.width, image.height
    for l in labels:
        g = _layout(d, font, fpx, l, 1.0, 0, 0, 0, 0, total_w, style,
                    clamp=False, maxw_override=maxw)
        xs = (g["ax"], g["tx"], g["x_end"])
        minx, maxx = min(minx, *xs), max(maxx, *xs)
        miny, maxy = min(miny, g["top"], g["ay"]), max(maxy, g["ty"], g["ay"])
    m = fpx * 0.6
    return (
        int(math.ceil(-minx + m)) if minx < 0 else 0,
        int(math.ceil(-miny + m)) if miny < 0 else 0,
        int(math.ceil(maxx - image.width + m)) if maxx > image.width else 0,
        int(math.ceil(maxy - image.height + m)) if maxy > image.height else 0,
    )