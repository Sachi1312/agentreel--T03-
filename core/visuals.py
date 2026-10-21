"""Procedural, original illustrations + frame renderer (PIL/numpy). No faces, no stock, no licences needed."""
import math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from .config import FONT_BOLD, FONT_MED, FONT_REG, LOGO, SAFE_TOP, SAFE_BOTTOM, DISCLOSURE

NAVY, NAVY2 = (9, 24, 48), (18, 62, 105)
TEAL, AMBER, WHITE, SKY = (46, 196, 182), (255, 183, 3), (255, 255, 255), (142, 202, 230)
_fonts = {}


def font(path, size):
    k = (str(path), size)
    if k not in _fonts:
        _fonts[k] = ImageFont.truetype(str(path), size)
    return _fonts[k]


def ease_out_back(x):
    x = min(max(x, 0), 1)
    c1, c3 = 1.4, 2.4
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def ease(x):
    x = min(max(x, 0), 1)
    return 1 - (1 - x) ** 3


# ------------------------------------------------------------------ layout
def layout(w, h):
    if h > w:  # 9:16
        return dict(w=w, h=h, icon_cy=630, icon_size=720, head_y=1010, head_font=74, head_w=920,
                    cap_y=1300, cap_font=58, cap_w=940, cap_lines=3, safe=(SAFE_TOP, h - SAFE_BOTTOM))
    return dict(w=w, h=h, icon_cy=330, icon_size=470, head_y=600, head_font=58, head_w=1500,
                cap_y=800, cap_font=52, cap_w=1500, cap_lines=2, safe=(0, h))


def wrap(text, fnt, max_w):
    words, lines, cur = text.split(), [], ""
    d = ImageDraw.Draw(Image.new("RGB", (4, 4)))
    for wd in words:
        t = (cur + " " + wd).strip()
        if d.textlength(t, font=fnt) <= max_w or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


# ------------------------------------------------------------------ icons (drawn at 1000x1000, supersampled)
def _rr(d, box, r, fill=None, outline=None, width=1):
    d.rounded_rectangle(box, r, fill=fill, outline=outline, width=width)


def _phone(d, cx=500, cy=500, w=430, h=780):
    x0, y0, x1, y1 = cx - w // 2, cy - h // 2, cx + w // 2, cy + h // 2
    _rr(d, (x0, y0, x1, y1), 70, fill=(235, 245, 255))
    _rr(d, (x0 + 22, y0 + 22, x1 - 22, y1 - 22), 52, fill=(14, 34, 66))
    _rr(d, (cx - 60, y0 + 34, cx + 60, y0 + 52), 9, fill=(40, 70, 110))
    return (x0 + 22, y0 + 22, x1 - 22, y1 - 22)


def _warn_tri(d, cx, cy, s, col=AMBER):
    d.polygon([(cx, cy - s), (cx + s * 1.05, cy + s * 0.8), (cx - s * 1.05, cy + s * 0.8)], fill=col)
    d.rounded_rectangle((cx - s * 0.09, cy - s * 0.4, cx + s * 0.09, cy + s * 0.22), 10, fill=NAVY)
    d.ellipse((cx - s * 0.1, cy + s * 0.34, cx + s * 0.1, cy + s * 0.54), fill=NAVY)


def _shield(d, cx, cy, s, fill=TEAL, check=True):
    pts = [(cx, cy - s)]
    for a in np.linspace(-1, 1, 14):
        pts.append((cx + a * s * 0.85, cy - s * 0.72 + abs(a) ** 2.2 * 0 + (a ** 2) * s * 0.18))
    for a in np.linspace(1, -1, 18):
        pts.append((cx + a * s * 0.85, cy - s * 0.54 + (1 - a ** 2) ** 0.5 * s * 1.45 * (abs(a) ** 0.35) * 0 + (1 - abs(a)) * s * 1.35 * (1 if True else 0)))
    d.polygon([(cx, cy - s), (cx + s * 0.85, cy - s * 0.65), (cx + s * 0.85, cy + s * 0.1),
               (cx + s * 0.45, cy + s * 0.65), (cx, cy + s), (cx - s * 0.45, cy + s * 0.65),
               (cx - s * 0.85, cy + s * 0.1), (cx - s * 0.85, cy - s * 0.65)], fill=fill)
    if check:
        d.line([(cx - s * 0.38, cy + s * 0.02), (cx - s * 0.08, cy + s * 0.33), (cx + s * 0.45, cy - s * 0.3)],
               fill=WHITE, width=int(s * 0.17), joint="curve")


def icon(kind, arg=None):
    S = 1000
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = lambda sz, p=FONT_BOLD: font(p, sz)
    if kind == "phone_call":
        sc = _phone(d)
        d.ellipse((380, 300, 620, 540), fill=(40, 80, 130))
        d.ellipse((445, 345, 555, 455), fill=SKY)
        d.pieslice((410, 440, 590, 620), 180, 360, fill=SKY)
        d.text((500, 600), "Unknown number", font=f(36, FONT_MED), fill=WHITE, anchor="mm")
        d.ellipse((350, 730, 450, 830), fill=(120, 130, 150))
        d.ellipse((550, 730, 650, 830), fill=TEAL)
        for r in (70, 120, 170):
            d.arc((500 - r, 255 - r, 500 + r, 255 + r), 215, 325, fill=(*AMBER, 255), width=10)
    elif kind == "phone_warning":
        _phone(d)
        _warn_tri(d, 500, 470, 190)
        d.text((500, 760), "VIDEO CALL", font=f(48), fill=SKY, anchor="mm")
    elif kind == "rupee_lock":
        _shield(d, 500, 470, 330, fill=(30, 80, 140), check=False)
        d.ellipse((330, 300, 670, 640), fill=AMBER)
        d.text((500, 470), "₹", font=f(250), fill=NAVY, anchor="mm")
        d.rounded_rectangle((590, 590, 800, 790), 28, fill=TEAL)
        d.arc((630, 490, 760, 640), 180, 360, fill=TEAL, width=26)
        d.ellipse((680, 660, 710, 690), fill=NAVY)
    elif kind == "briefcase":
        d.arc((380, 210, 620, 450), 180, 360, fill=SKY, width=34)
        _rr(d, (190, 320, 810, 760), 60, fill=(30, 80, 140))
        d.rectangle((190, 510, 810, 540), fill=(18, 50, 95))
        _rr(d, (455, 490, 545, 580), 14, fill=AMBER)
        d.ellipse((600, 640, 860, 900), fill=TEAL)
        d.text((730, 770), "₹", font=f(170), fill=WHITE, anchor="mm")
        d.line([(630, 880), (830, 660)], fill=(*NAVY, 255), width=26)
    elif kind == "chat_shield":
        _rr(d, (130, 230, 640, 520), 70, fill=SKY)
        d.polygon([(220, 515), (200, 640), (340, 515)], fill=SKY)
        for i in range(3):
            d.ellipse((260 + i * 100, 350, 310 + i * 100, 400), fill=NAVY)
        _rr(d, (380, 440, 880, 700), 70, fill=(60, 110, 170))
        d.polygon([(780, 695), (810, 800), (700, 695)], fill=(60, 110, 170))
        _shield(d, 700, 760, 170, fill=TEAL)
    elif kind == "big_text":
        d.ellipse((120, 120, 880, 880), fill=(18, 50, 95))
        d.ellipse((150, 150, 850, 850), outline=TEAL, width=22)
        d.text((500, 430), str(arg or ""), font=f(240 if len(str(arg or "")) <= 5 else 150), fill=WHITE, anchor="mm")
        d.rounded_rectangle((300, 590, 700, 690), 50, fill=TEAL)
        d.text((500, 640), "CALL NOW", font=f(54), fill=NAVY, anchor="mm")
    elif kind == "portal":
        _rr(d, (90, 200, 910, 800), 50, fill=(235, 245, 255))
        d.rounded_rectangle((90, 200, 910, 330), 50, fill=(60, 110, 170))
        d.rectangle((90, 280, 910, 330), fill=(60, 110, 170))
        for i, c in enumerate([(255, 95, 86), AMBER, (39, 201, 63)]):
            d.ellipse((130 + i * 55, 245, 160 + i * 55, 275), fill=c)
        _rr(d, (130, 340, 870, 420), 38, fill=WHITE, outline=(150, 175, 205), width=4)
        txt = str(arg or "")
        d.text((170, 380), txt, font=f(46 if len(txt) < 20 else 36, FONT_MED), fill=(18, 50, 95), anchor="lm")
        d.rounded_rectangle((300, 560, 700, 670), 55, fill=TEAL)
        d.text((500, 615), "REPORT", font=f(58), fill=NAVY, anchor="mm")
        d.rounded_rectangle((200, 470, 800, 500), 14, fill=(200, 215, 235))
    else:  # shield (default)
        _shield(d, 500, 500, 400)
    return im


def render_icon(kind, arg, size):
    im = icon(kind, arg).filter(ImageFilter.GaussianBlur(0.6))
    return im.resize((size, size), Image.LANCZOS)


# ------------------------------------------------------------------ background
def gradient(w, h, shift=0.0):
    y = np.linspace(0, 1, h)[:, None, None]
    x = np.linspace(0, 1, w)[None, :, None]
    t = np.clip(0.55 * y + 0.35 * x + shift, 0, 1)
    c1, c2 = np.array(NAVY, float), np.array(NAVY2, float)
    return (c1 + (c2 - c1) * t).astype(np.uint8).repeat(1, axis=2) if False else (c1 + (c2 - c1) * t).astype(np.uint8)


class Particles:
    def __init__(self, w, h, n=22, seed=0):
        r = random.Random(seed)
        self.p = [(r.random() * w, r.random() * h, r.uniform(4, 12), r.uniform(18, 60), r.random() * 6.28) for _ in range(n)]
        self.w, self.h = w, h

    def draw(self, d, t):
        for x, y, rad, sp, ph in self.p:
            yy = (y - sp * t) % self.h
            xx = x + 14 * math.sin(t * 0.8 + ph)
            d.ellipse((xx - rad, yy - rad, xx + rad, yy + rad), fill=(30 + int(25 * math.sin(ph)), 90, 130))


# ------------------------------------------------------------------ text helpers
def draw_text_block(img, d, lines, fnt, cx, y, fill, line_gap=1.22, shadow=True, report=None, kind="text", shot=None):
    asc = fnt.size
    boxes = []
    for i, ln in enumerate(lines):
        yy = y + int(i * asc * line_gap)
        if shadow:
            d.text((cx + 3, yy + 4), ln, font=fnt, fill=(0, 8, 20), anchor="ma")
        d.text((cx, yy), ln, font=fnt, fill=fill, anchor="ma")
        bb = d.textbbox((cx, yy), ln, font=fnt, anchor="ma")
        boxes.append(bb)
        if report is not None:
            report.append({"shot": shot, "kind": kind, "text": ln, "font_px": fnt.size, "bbox": list(bb)})
    return boxes


def draw_caption(img, lay, text, alpha, report=None, shot=None):
    if not text or alpha <= 0:
        return
    fnt = font(FONT_BOLD, lay["cap_font"])
    lines = wrap(text, fnt, lay["cap_w"])[: lay["cap_lines"]]
    pad = 26
    hh = int(len(lines) * fnt.size * 1.25) + pad * 2
    box = Image.new("RGBA", (lay["w"], lay["h"]), (0, 0, 0, 0))
    bd = ImageDraw.Draw(box)
    y0 = lay["cap_y"]
    maxw = max(bd.textlength(l, font=fnt) for l in lines)
    bd.rounded_rectangle((lay["w"] / 2 - maxw / 2 - pad - 10, y0 - pad, lay["w"] / 2 + maxw / 2 + pad + 10, y0 - pad + hh), 34,
                         fill=(5, 15, 32, int(190 * alpha)))
    img.alpha_composite(box)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    draw_text_block(layer, ld, lines, fnt, lay["w"] // 2, y0, (255, 255, 255, int(255 * alpha)), shadow=False,
                    report=report, kind="caption", shot=shot)
    img.alpha_composite(layer)
    if report is not None:
        report.append({"shot": shot, "kind": "caption_box", "text": "", "font_px": fnt.size,
                       "bbox": [lay["w"] / 2 - maxw / 2 - pad, y0 - pad, lay["w"] / 2 + maxw / 2 + pad, y0 - pad + hh]})


# ------------------------------------------------------------------ frames
class Renderer:
    def __init__(self, w, h, shots, captions, seed=42):
        self.w, self.h, self.shots, self.captions = w, h, shots, captions
        self.lay = layout(w, h)
        self.bgs = [Image.fromarray(gradient(w, h, 0.06 * (i % 3) - 0.05)).convert("RGBA") for i in range(len(shots))]
        self.parts = [Particles(w, h, seed=seed + i) for i in range(len(shots))]
        self.icons = {}
        for i, s in enumerate(shots):
            if s["visual"] != "endcard":
                kind, _, arg = s["visual"].partition(":")
                self.icons[i] = render_icon(kind, arg or None, self.lay["icon_size"])
        self.report = []
        self._logo = None

    def logo(self, target_h):
        """Official logo, unmodified, on a white rounded card (the maroon logo needs a light background)."""
        if self._logo is None or self._logo.height != target_h:
            lg = Image.open(LOGO).convert("RGB")
            pad = int(target_h * 0.07)
            ih = target_h - 2 * pad
            lg = lg.resize((int(lg.width * ih / lg.height), ih), Image.LANCZOS)      # uniform scale only
            card = Image.new("RGBA", (lg.width + 2 * pad, target_h), (0, 0, 0, 0))
            ImageDraw.Draw(card).rounded_rectangle((0, 0, card.width - 1, card.height - 1), int(target_h * 0.09), fill=(255, 255, 255, 255))
            card.paste(lg, (pad, pad))
            self._logo = card
        return self._logo

    def shot_frame(self, i, t, record=False):
        s = self.shots[i]
        u = t - s["start"]
        lay = self.lay
        img = self.bgs[i].copy()
        d = ImageDraw.Draw(img)
        self.parts[i].draw(d, t)
        rep = self.report if record else None
        if s["visual"] == "endcard":
            self._endcard(img, d, u, rep, i)
            return img
        # icon with pop-in + gentle bob
        sc = ease_out_back(u / 0.55)
        ic = self.icons[i]
        size = max(int(ic.width * sc * (1 + 0.012 * math.sin(u * 2.2))), 8)
        im2 = ic.resize((size, size), Image.BILINEAR)
        cy = lay["icon_cy"] + 8 * math.sin(u * 1.7)
        img.alpha_composite(im2, (int(lay["w"] / 2 - size / 2), int(cy - size / 2)))
        # headline
        a = ease((u - 0.2) / 0.4)
        if s["on_screen_text"]:
            hl = font(FONT_BOLD, lay["head_font"])
            lines = wrap(s["on_screen_text"], hl, lay["head_w"])[:2]
            layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
            ld = ImageDraw.Draw(layer)
            draw_text_block(layer, ld, lines, hl, lay["w"] // 2, lay["head_y"] + int((1 - a) * 24),
                            (*AMBER, int(255 * a)), shadow=False, report=rep, kind="headline", shot=s["id"])
            img.alpha_composite(layer)
        # caption chunk
        for c in self.captions:
            if c["start"] <= t < c["end"]:
                draw_caption(img, lay, c["text"], ease((t - c["start"]) / 0.18), rep, s["id"])
                break
        return img

    def _endcard(self, img, d, u, rep, i):
        lay, s = self.lay, self.shots[i]
        w, h = lay["w"], lay["h"]
        a = ease(u / 0.5)
        lg = self.logo(int(h * 0.24) if h > w else int(h * 0.36))
        top = SAFE_TOP + 90 if h > w else 40
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        lg2 = lg.copy()
        lg2.putalpha(lg2.getchannel("A").point(lambda v: int(v * a)))
        layer.alpha_composite(lg2, (int(w / 2 - lg.width / 2), top))
        if rep is not None:
            rep.append({"shot": s["id"], "kind": "logo", "text": "", "font_px": 0, "bbox": [w / 2 - lg.width / 2, top, w / 2 + lg.width / 2, top + lg.height]})
        ld = ImageDraw.Draw(layer)
        y = top + lg.height + (70 if h > w else 40)
        cta = font(FONT_BOLD, 62 if h > w else 54)
        lines = wrap(s["on_screen_text"], cta, lay["cap_w"])
        b = draw_text_block(layer, ld, lines, cta, w // 2, y, (*AMBER, int(255 * a)), shadow=False, report=rep, kind="cta", shot=s["id"])
        y = b[-1][3] + (70 if h > w else 30)
        sm = font(FONT_MED, 40 if h > w else 38)
        dl = wrap(DISCLOSURE, sm, lay["cap_w"])
        draw_text_block(layer, ld, dl, sm, w // 2, y, (*SKY, int(255 * a)), shadow=False, report=rep, kind="disclosure", shot=s["id"])
        img.alpha_composite(layer)

    def frame(self, t, record=False):
        i = max(k for k, s in enumerate(self.shots) if s["start"] <= t + 1e-9)
        img = self.shot_frame(i, t, record)
        u = t - self.shots[i]["start"]
        if i > 0 and u < 0.25:
            prev = self.shot_frame(i - 1, self.shots[i]["start"] - 1e-3)
            img = Image.blend(prev, img, ease(u / 0.25))
        return img.convert("RGB")
