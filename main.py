#!/usr/bin/env python3
"""The picture that tastes of one — a bowl of ramen, one hero ingredient.

Procedural per-pixel render, pure stdlib (zlib + struct PNG encoder).
Canvas 768x768. Output: /output/entry.png (or argv[1] for local tests).
Deterministic: fixed seed, no randomness, no network, no assets.
"""
import math
import os
import struct
import sys
import time
import zlib

W = H = 768
CX, CY = 384, 400          # bowl centre
R_OUT = 348                # bowl outer radius
R_LIP = 320                # inner lip radius
R_BROTH = 312              # broth radius


def clamp(v, lo=0, hi=255):
    v = int(round(v))
    return lo if v < lo else hi if v > hi else v


def hash2(ix, iy, seed):
    """Deterministic [0,1) hash from two ints + seed."""
    h = (ix * 374761393 + iy * 668265263 + seed * 2246822519) & 0xFFFFFFFF
    h ^= h >> 13
    h = (h * 1274126177) & 0xFFFFFFFF
    h ^= h >> 16
    return h / 4294967296.0


def smooth(a, b, x):
    t = (x - a) / (b - a)
    t = 0.0 if t < 0.0 else 1.0 if t > 1.0 else t
    return t * t * (3.0 - 2.0 * t)


# ---------------------------------------------------------------- precompute
# Noodle warp per column: warped_y = y - warp[x]
warp = [18.0 * math.sin(x * 0.02 + 1.3)
        + 10.0 * math.sin(x * 0.043 + 4.0)
        - 6.0 * math.sin(x * 0.008 + 2.0) for x in range(W)]

# Tone per strand index (strands differ slightly in tone).
strand_tone = {s: 0.90 + 0.18 * hash2(s, 3, 5) for s in range(-4, 36)}

# Missing strand segments are chosen per (segment, strand) cell, see render().

# Chili-oil droplets: ~1 in 10 cells on a 26px grid, dark red + bright core.
chili = []
for i in range(W // 26 + 1):
    for j in range(H // 26 + 1):
        if hash2(i, j, 21) < 0.10:
            ox = (hash2(i, j, 22) - 0.5) * 10.0
            oy = (hash2(i, j, 23) - 0.5) * 10.0
            px, py = i * 26 + 13 + ox, j * 26 + 13 + oy
            if (px - CX) ** 2 + (py - CY) ** 2 < 300.0 ** 2:
                chili.append((px, py))

# Green-onion rings: ~1 in 8 cells on a 34px grid, flattened ellipses.
onion = []
for i in range(W // 34 + 1):
    for j in range(H // 34 + 1):
        if hash2(i, j, 31) < 0.125:
            ox = (hash2(i, j, 32) - 0.5) * 12.0
            oy = (hash2(i, j, 33) - 0.5) * 12.0
            px, py = i * 34 + 17 + ox, j * 34 + 17 + oy
            if (px - CX) ** 2 + (py - CY) ** 2 < 298.0 ** 2:
                onion.append((px, py))

# Broth radial gradient lookup by integer radius (centre -> edge).
broth_lut = []
for r in range(R_BROTH + 1):
    t = r / R_BROTH
    u = t ** 1.15
    broth_lut.append((
        int(206 + (88 - 206) * u),
        int(140 + (48 - 140) * u),
        int(60 + (22 - 60) * u),
    ))

# Nori rotation constants (-20 degrees).
NORI_CX, NORI_CY = 212.0, 268.0
COS_N, SIN_N = math.cos(math.radians(20.0)), math.sin(math.radians(20.0))

# Eggs: (white cx, cy, rx, ry, yolk r).
EGGS = [(298.0, 322.0, 84.0, 76.0, 44.0),
        (478.0, 330.0, 82.0, 74.0, 42.0)]

# Chopsticks: axis through (560,210), direction (0.82,-0.57).
CHOP_PX, CHOP_PY = 560.0, 210.0
CHOP_DX, CHOP_DY = 0.82, -0.57
CHOP_NX, CHOP_NY = 0.57, 0.82

# Steam columns: (base x, phase, sigma).
STEAM = [(300.0, 0.0, 30.0), (384.0, 2.1, 34.0), (468.0, 4.2, 30.0)]


def render():
    img = bytearray(W * H * 3)
    sin = math.sin
    sqrt = math.sqrt
    atan2 = math.atan2
    pi = math.pi

    for y in range(H):
        dy = y - CY
        dy2 = dy * dy
        row = y * W * 3
        w_y = y  # warped noodle coordinate base
        for x in range(W):
            dx = x - CX
            r2 = dx * dx + dy2
            o = row + x * 3
            if r2 > R_OUT * R_OUT:
                # ---- background: warm near-black, orange glow, brighter top
                gx, gy2 = x - CX, y - 280.0
                g = math.exp(-(gx * gx + gy2 * gy2) / (2.0 * 380.0 * 380.0))
                top = (1.0 - y / H) * 9.0
                img[o] = clamp(14 + 110 * g * 0.55 + top)
                img[o + 1] = clamp(9 + 48 * g * 0.55 + top * 0.55)
                img[o + 2] = clamp(7 + 16 * g * 0.55 + top * 0.25)
            elif r2 > R_LIP * R_LIP:
                # ---- bowl ceramic, very dark, top slightly lighter
                shade = 0.90 + 0.20 * (1.0 - (y - 52) / 696.0)
                r = 25 * shade
                g = 19 * shade
                b = 17 * shade
                rr = sqrt(r2)
                if 326.0 <= rr <= 346.0:
                    # warm arc highlight on the upper lip (light, upper left)
                    ang = atan2(dy, dx) * 180.0 / pi
                    if -175.0 <= ang <= -95.0:
                        fall = sin((ang + 175.0) / 80.0 * pi)
                        r += 150 * fall * 0.55
                        g += 95 * fall * 0.55
                        b += 45 * fall * 0.55
                if rr >= 344.0:  # outer edge definition
                    r *= 0.8
                    g *= 0.8
                    b *= 0.8
                img[o] = clamp(r)
                img[o + 1] = clamp(g)
                img[o + 2] = clamp(b)
            elif r2 > R_BROTH * R_BROTH:
                # ---- lip ring, thin lighter line right at the edge
                if sqrt(r2) >= 318.0:
                    img[o], img[o + 1], img[o + 2] = 74, 56, 44
                else:
                    img[o], img[o + 1], img[o + 2] = 52, 38, 30
            else:
                # ---- broth + noodles
                r = int(sqrt(r2))
                br, bg, bb = broth_lut[r]
                # subtle swirl modulation
                sw = sin(atan2(dy, dx) * 3.0 + r * 0.045) * 0.05
                br = br * (1.0 + sw)
                bg = bg * (1.0 + sw)
                bb = bb * (1.0 + sw)
                # glossy light pool, upper left of the broth
                ex = (x - 300.0) / 130.0
                ey = (y - 250.0) / 75.0
                ed = ex * ex + ey * ey
                if ed < 1.0:
                    pool = 0.28 * (1.0 - ed)
                    br += 230 * pool
                    bg += 175 * pool
                    bb += 95 * pool
                warped = w_y - warp[x]
                m = warped % 26.0
                if m < 10.0:
                    # noodle strand: pale cream, bright ridge, darker groove edge
                    # ~1 in 5 strand segments is missing, showing glossy broth
                    s = int(warped // 26)
                    if hash2(x // 44, s, 11) < 0.20:
                        img[o] = clamp(br * 1.12 + 20)
                        img[o + 1] = clamp(bg * 1.12 + 12)
                        img[o + 2] = clamp(bb * 1.12 + 5)
                    else:
                        p = m / 10.0
                        ridge = 0.80 + 0.30 * sin(pi * p)
                        tone = strand_tone[s]
                        img[o] = clamp(236 * tone * ridge)
                        img[o + 1] = clamp(206 * tone * ridge)
                        img[o + 2] = clamp(152 * tone * ridge)
                else:
                    # groove: shadowed broth between strands
                    img[o] = clamp(br * 0.82)
                    img[o + 1] = clamp(bg * 0.82)
                    img[o + 2] = clamp(bb * 0.82)

    # ---- nori: dark green-black rotated rectangle, behind the eggs
    for y in range(186, 351):
        for x in range(117, 308):
            lx, ly = x - NORI_CX, y - NORI_CY
            u = COS_N * lx + SIN_N * ly
            v = -SIN_N * lx + COS_N * ly
            if abs(u) < 80.0 and abs(v) < 58.0:
                o = (y * W + x) * 3
                r, g, b = 13.0, 23.0, 15.0
                if abs(u) > 76.0 or abs(v) > 54.0:  # edge
                    r, g, b = 28.0, 44.0, 30.0
                elif (u + v) % 100.0 < 20.0:  # faint diagonal sheen
                    r, g, b = 31.0, 53.0, 33.0
                img[o] = clamp(r)
                img[o + 1] = clamp(g)
                img[o + 2] = clamp(b)

    # ---- chili-oil droplets: dark red with a bright orange-red core
    for (px, py) in chili:
        x0, x1 = int(px - 7), int(px + 8)
        y0, y1 = int(py - 7), int(py + 8)
        for y in range(max(0, y0), min(H, y1)):
            for x in range(max(0, x0), min(W, x1)):
                d = math.hypot(x - px, y - py)
                if d < 6.5:
                    o = (y * W + x) * 3
                    a = smooth(6.5, 5.0, d)
                    if d < 2.5:
                        cr, cg, cb = 255.0, 92.0, 32.0
                    else:
                        cr, cg, cb = 158.0, 34.0, 16.0
                    if math.hypot(x - (px - 1.5), y - (py - 1.5)) < 1.1:
                        cr, cg, cb = 255.0, 160.0, 90.0
                    img[o] = clamp(img[o] * (1 - a) + cr * a)
                    img[o + 1] = clamp(img[o + 1] * (1 - a) + cg * a)
                    img[o + 2] = clamp(img[o + 2] * (1 - a) + cb * a)

    # ---- green-onion rings: dark green ring, light green centre
    for (px, py) in onion:
        x0, x1 = int(px - 9), int(px + 10)
        y0, y1 = int(py - 7), int(py + 8)
        for y in range(max(0, y0), min(H, y1)):
            for x in range(max(0, x0), min(W, x1)):
                ex = (x - px) / 7.5
                ey = (y - py) / 5.2
                d = ex * ex + ey * ey
                if d < 1.05:
                    o = (y * W + x) * 3
                    a = smooth(1.05, 0.9, d)
                    if d > 0.45:
                        cr, cg, cb = 52.0, 128.0, 58.0
                    else:
                        cr, cg, cb = 168.0, 224.0, 130.0
                    img[o] = clamp(img[o] * (1 - a) + cr * a)
                    img[o + 1] = clamp(img[o + 1] * (1 - a) + cg * a)
                    img[o + 2] = clamp(img[o + 2] * (1 - a) + cb * a)

    # ---- ajitama egg halves: soft shadow, ivory white, golden yolk
    for (ecx, ecy, erx, ery, yr) in EGGS:
        # drop shadow, slightly larger ellipse shifted down
        x0, x1 = int(ecx - erx - 16), int(ecx + erx + 17)
        y0, y1 = int(ecy - ery - 6), int(ecy + ery + 19)
        for y in range(max(0, y0), min(H, y1)):
            for x in range(max(0, x0), min(W, x1)):
                sx = (x - (ecx + 6)) / (erx + 8)
                sy = (y - (ecy + 10)) / (ery + 8)
                d = sx * sx + sy * sy
                if d < 1.0:
                    o = (y * W + x) * 3
                    f = 1.0 - 0.35 * (1.0 - d)
                    img[o] = clamp(img[o] * f)
                    img[o + 1] = clamp(img[o + 1] * f)
                    img[o + 2] = clamp(img[o + 2] * f)
        # white: bright ivory centre, warmer edge
        x0, x1 = int(ecx - erx - 2), int(ecx + erx + 3)
        y0, y1 = int(ecy - ery - 2), int(ecy + ery + 3)
        for y in range(max(0, y0), min(H, y1)):
            for x in range(max(0, x0), min(W, x1)):
                ex = (x - ecx) / erx
                ey = (y - ecy) / ery
                d = ex * ex + ey * ey
                if d < 1.0:
                    f = 1.0 - sqrt(d)
                    a = smooth(0.0, 0.08, f)
                    cr = 226 + (252 - 226) * f
                    cg = 203 + (246 - 203) * f
                    cb = 168 + (232 - 168) * f
                    o = (y * W + x) * 3
                    img[o] = clamp(img[o] * (1 - a) + cr * a)
                    img[o + 1] = clamp(img[o + 1] * (1 - a) + cg * a)
                    img[o + 2] = clamp(img[o + 2] * (1 - a) + cb * a)
        # yolk: dark orange edge -> bright golden centre, shifted down-right
        ycx, ycy = ecx + 8.0, ecy + 10.0
        x0, x1 = int(ycx - yr - 2), int(ycx + yr + 3)
        y0, y1 = int(ycy - yr - 2), int(ycy + yr + 3)
        for y in range(max(0, y0), min(H, y1)):
            for x in range(max(0, x0), min(W, x1)):
                d = math.hypot(x - ycx, y - ycy) / yr
                if d < 1.0:
                    f = (1.0 - d) ** 0.8
                    a = smooth(0.0, 0.06, 1.0 - d)
                    cr = 196 + (255 - 196) * f
                    cg = 96 + (192 - 96) * f
                    cb = 22 + (64 - 22) * f
                    if 0.78 < d < 0.88:  # faint spot ring near the edge
                        cr = cr * 0.65 + 205 * 0.35
                        cg = cg * 0.65 + 112 * 0.35
                        cb = cb * 0.65 + 30 * 0.35
                    if math.hypot(x - (ycx - 15), y - (ycy - 15)) < 5.5:
                        cr, cg, cb = 255.0, 232.0, 165.0
                    o = (y * W + x) * 3
                    img[o] = clamp(img[o] * (1 - a) + cr * a)
                    img[o + 1] = clamp(img[o + 1] * (1 - a) + cg * a)
                    img[o + 2] = clamp(img[o + 2] * (1 - a) + cb * a)

    # ---- chopsticks: two dark wood sticks on the upper-right lip
    for y in range(0, 341):
        for x in range(390, W):
            t = (x - CHOP_PX) * CHOP_DX + (y - CHOP_PY) * CHOP_DY
            s = (x - CHOP_PX) * CHOP_NX + (y - CHOP_PY) * CHOP_NY
            if -185.0 <= t <= 335.0:
                stick = None
                if 2.0 <= s <= 16.0:
                    stick = 1
                elif -16.0 <= s <= -2.0:
                    stick = 2
                if stick is not None:
                    o = (y * W + x) * 3
                    r, g, b = 54.0, 36.0, 22.0
                    # brighter upper edge of each stick
                    if (stick == 1 and s < 4.5) or (stick == 2 and s > -13.5):
                        r, g, b = 150.0, 102.0, 56.0
                    img[o] = clamp(r)
                    img[o + 1] = clamp(g)
                    img[o + 2] = clamp(b)

    # ---- steam: three soft white columns rising from the broth
    for (bx, phase, sigma) in STEAM:
        x0, x1 = int(bx - 48), int(bx + 49)
        for y in range(40, 326):
            rise = smooth(325.0, 260.0, 325.0 - y) if y > 260 else 1.0
            fall = smooth(40.0, 190.0, y)
            env = rise * fall
            if env <= 0.0:
                continue
            cx = bx + 13.0 * sin((325.0 - y) * 0.016 + phase) \
                + 5.0 * sin((325.0 - y) * 0.047 + phase * 2.3)
            for x in range(max(0, x0), min(W, x1)):
                dd = (x - cx) / sigma
                a = 0.45 * env * math.exp(-dd * dd)
                if a > 0.004:
                    o = (y * W + x) * 3
                    img[o] = clamp(img[o] * (1 - a) + 255 * a)
                    img[o + 1] = clamp(img[o + 1] * (1 - a) + 245 * a)
                    img[o + 2] = clamp(img[o + 2] * (1 - a) + 235 * a)

    # ---- vignette + light grain
    for y in range(H):
        dy = y - 384.0
        row = y * W * 3
        for x in range(W):
            dx = x - 384.0
            d = sqrt(dx * dx + dy * dy) / 544.0
            vig = 1.0 - 0.30 * d * d
            grain = int(hash2(x, y, 7) * 9.0) - 4
            o = row + x * 3
            img[o] = clamp(img[o] * vig + grain)
            img[o + 1] = clamp(img[o + 1] * vig + grain)
            img[o + 2] = clamp(img[o + 2] * vig + grain)
    return img


def write_png(path, img):
    raw = bytearray()
    stride = W * 3
    for y in range(H):
        raw.append(0)
        raw += img[y * stride:(y + 1) * stride]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(typ, data):
        return (struct.pack(">I", len(data)) + typ + data
                + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
           + chunk(b"IDAT", comp) + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "/output/entry.png"
    t0 = time.time()
    img = render()
    t1 = time.time()
    d = os.path.dirname(out)
    if d:
        os.makedirs(d, exist_ok=True)
    size = write_png(out, img)
    print(f"rendered {W}x{H} in {t1 - t0:.2f}s -> {out} ({size} bytes)")
    assert size <= 1048576, "PNG over 1 MiB"


if __name__ == "__main__":
    main()
