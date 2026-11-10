#!/usr/bin/env python3
"""Sestaví data 3D ukázky z podkladů stažených skriptem fetch_slice3d.py.

Výstup: prototype/hostivice3d/world.json a ortho.jpg.
Souřadnice: x = východ, z = jih (metry od SZ rohu výřezu), y = výška nad nejnižším bodem terénu.
"""
import base64, json, math
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

Image.MAX_IMAGE_PIXELS = None
X0, X1, Y0, Y1 = -754950, -754150, -1042400, -1041600
N = X1 - X0
SRC = Path(__file__).parent / "data" / "slice3d"
OUT = Path(__file__).parents[2] / "prototype" / "hostivice3d"
OUT.mkdir(parents=True, exist_ok=True)
L = lambda p: (p[0] - X0, Y1 - p[1])
load = lambda n: json.loads((SRC / f"{n}.json").read_text())

dmr = np.load(SRC / "dmr5g.npy"); dmp = np.load(SRC / "dmp1g.npy")
dmp = np.where(dmp < -1000, dmr, dmp)
hmin = float(dmr.min()); obj = np.maximum(dmp - dmr, 0)
ter = dmr - hmin
G = 4
grid = ter[np.minimum(np.arange(0, N + 1, G), N - 1)][:, np.minimum(np.arange(0, N + 1, G), N - 1)]
th = lambda x, z: float(ter[int(min(max(z, 0), N - 1)), int(min(max(x, 0), N - 1))])


def simplify(pts, eps):
    if len(pts) < 3: return pts
    a, b = pts[0], pts[-1]; dx, dy = b[0] - a[0], b[1] - a[1]; d = math.hypot(dx, dy) or 1e-9
    best, bi = 0, 0
    for i in range(1, len(pts) - 1):
        dist = abs((pts[i][0] - a[0]) * dy - (pts[i][1] - a[1]) * dx) / d
        if dist > best: best, bi = dist, i
    if best <= eps: return [a, b]
    return simplify(pts[:bi + 1], eps)[:-1] + simplify(pts[bi:], eps)


def area(p): return sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p))) / 2
def centroid(p): return (sum(q[0] for q in p) / len(p), sum(q[1] for q in p) / len(p))
r1 = lambda v: round(v, 1)

# ---------------------------------------------------------------- budovy
mask_all = Image.new("L", (N, N), 0); draw_all = ImageDraw.Draw(mask_all)
budovy = []
for f in load("budovy"):
    ring = [L(p) for p in f["geometry"]["rings"][0]]
    if ring[0] == ring[-1]: ring = ring[:-1]
    half = len(ring) // 2
    ring = simplify(ring[:half + 1], 0.35)[:-1] + simplify(ring[half:] + [ring[0]], 0.35)[:-1]
    if len(ring) < 3: continue
    cx, cz = centroid(ring)
    if not (4 < cx < N - 4 and 4 < cz < N - 4): continue
    if area(ring) < 0: ring = ring[::-1]            # jednotná orientace
    A = abs(area(ring))
    if A < 12: continue
    m = Image.new("L", (N, N), 0); ImageDraw.Draw(m).polygon(ring, fill=1)
    mm = np.array(m, bool)
    if mm.sum() < 6: continue
    hh = obj[mm]; base = float(ter[mm].min())
    ridge = float(np.percentile(hh, 93)); eave = float(np.percentile(hh, 28))
    if ridge < 2.2:                                   # sken budovu nezachytil (novostavba, demolice)
        floors = f["attributes"].get("pocetpodlazi") or 1
        ridge = 3.0 * floors + 1.5; eave = 3.0 * floors
    pitched = (ridge - eave) > 1.3 and A < 700
    if pitched: eave = max(2.4, min(eave, ridge - 1.2))
    else: eave = max(2.4, float(np.percentile(hh, 70)) if hh.max() > 2.2 else eave); ridge = eave
    # orientovaný obdélník přes nejdelší hranu
    best = None
    for i in range(len(ring)):
        a, b = ring[i], ring[(i + 1) % len(ring)]
        ang = math.atan2(b[1] - a[1], b[0] - a[0]); c, s = math.cos(-ang), math.sin(-ang)
        rot = [(p[0] * c - p[1] * s, p[0] * s + p[1] * c) for p in ring]
        xs, ys = [p[0] for p in rot], [p[1] for p in rot]
        w, h = max(xs) - min(xs), max(ys) - min(ys)
        if best is None or w * h < best[0]:
            mx, my = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
            best = (w * h, ang, w, h, mx * math.cos(ang) - my * math.sin(ang), mx * math.sin(ang) + my * math.cos(ang))
    typ = 0
    if pitched: typ = 1 if A / best[0] > 0.86 and min(best[2], best[3]) < 15 else 2
    b = {"p": [[r1(x), r1(z)] for x, z in ring], "b": r1(base), "e": r1(eave), "r": r1(ridge), "t": typ, "a": round(A)}
    if typ == 1: b["o"] = [r1(best[4]), r1(best[5]), round(best[1], 3), r1(best[2]), r1(best[3])]
    budovy.append(b); draw_all.polygon(ring, fill=255)
bmask = np.array(mask_all) > 0

# ---------------------------------------------------------------- ulice
def paths(name, w, auto):
    out = []
    for f in load(name):
        for path in f["geometry"]["paths"]:
            pts = [L(p) for p in path]
            pts = [p for p in pts if -30 <= p[0] <= N + 30 and -30 <= p[1] <= N + 30]
            if len(pts) >= 2: out.append({"p": [[r1(x), r1(z)] for x, z in pts], "w": w, "a": auto})
    return out
ulice = paths("silnice", 7.5, 1) + paths("ulice", 5.5, 1) + paths("cesty", 2.2, 0)
trat = [[[r1(x), r1(z)] for x, z in map(L, path)] for f in load("trat") for path in f["geometry"]["paths"]]
voda = [[[r1(x), r1(z)] for x, z in map(L, f["geometry"]["rings"][0])] for f in load("voda")]
parkoviste = [[L(p) for p in f["geometry"]["rings"][0]] for f in load("parkoviste")]

ins = lambda p: 25 < p[0] < N - 25 and 25 < p[1] < N - 25
segs = [(s["p"][i], s["p"][i + 1]) for s in ulice if s["a"] for i in range(len(s["p"]) - 1) if ins(s["p"][i]) and ins(s["p"][i + 1])]
def nearest_street(pt):
    best = None
    for a, b in segs:
        dx, dz = b[0] - a[0], b[1] - a[1]; l2 = dx * dx + dz * dz or 1e-9
        t = max(0, min(1, ((pt[0] - a[0]) * dx + (pt[1] - a[1]) * dz) / l2))
        q = (a[0] + dx * t, a[1] + dz * t); d = math.hypot(q[0] - pt[0], q[1] - pt[1])
        if best is None or d < best[0]: best = (d, q, math.atan2(dz, dx))
    return best
inside = lambda x, z: 0 <= int(x) < N and 0 <= int(z) < N and bmask[int(z), int(x)]

# ---------------------------------------------------------------- stromy
road = Image.new("L", (N, N), 0); rd = ImageDraw.Draw(road)
for s in ulice:
    if s["a"]: rd.line([tuple(p) for p in s["p"]], fill=255, width=int(s["w"]) + 1)
for t in trat: rd.line([tuple(p) for p in t], fill=255, width=26)
blocked = bmask | (np.array(road) > 0)
bl = np.array(Image.fromarray((bmask * 255).astype(np.uint8)).resize((N, N)).filter(__import__("PIL.ImageFilter", fromlist=["x"]).MaxFilter(5))) > 0
# DMP 1G ze služby vegetaci neobsahuje, koruny stromů proto hledáme v ortofotu (tmavá zeleň).
om = np.asarray(Image.open(SRC / "ortho.png").convert("RGB").resize((N, N), Image.BOX), np.float32)
R_, G_, B_ = om[..., 0], om[..., 1], om[..., 2]
lum = 0.3 * R_ + 0.59 * G_ + 0.11 * B_
veg = (G_ >= R_) & (G_ > B_ * 1.03) & (lum < 105)
stromy = []
B = 7
rng = np.random.default_rng(7)
for z0 in range(0, N - B, B):
    for x0 in range(0, N - B, B):
        free = ~(bl | blocked)[z0:z0 + B, x0:x0 + B]
        if free.mean() < 0.9 or veg[z0:z0 + B, x0:x0 + B].mean() < 0.6: continue
        stromy.append([x0 + int(rng.integers(1, B - 1)), z0 + int(rng.integers(1, B - 1)), r1(float(rng.uniform(7, 15)))])

# ---------------------------------------------------------------- lampy
lampy = []
for s in ulice:
    if not s["a"]: continue
    acc = 12.0
    for i in range(len(s["p"]) - 1):
        a, b = s["p"][i], s["p"][i + 1]; dx, dz = b[0] - a[0], b[1] - a[1]; ln = math.hypot(dx, dz)
        if ln < 0.1: continue
        while acc < ln:
            t = acc / ln; off = s["w"] / 2 + 1.2
            x, z = a[0] + dx * t - dz / ln * off, a[1] + dz * t + dx / ln * off
            if 5 < x < N - 5 and 5 < z < N - 5 and not inside(x, z) and all(math.hypot(x - q[0], z - q[1]) > 18 for q in lampy):
                lampy.append([r1(x), r1(z)])
            acc += 34
        acc -= ln

# ---------------------------------------------------------------- místa pro mise
def building_near(pt, amin=90, amax=5000, skip=()):
    c = [(math.hypot(centroid(b["p"])[0] - pt[0], centroid(b["p"])[1] - pt[1]), i) for i, b in enumerate(budovy) if amin <= b["a"] <= amax and i not in skip]
    return min(c)[1]
def door(bi):
    b = budovy[bi]; c = centroid(b["p"]); d, q, ang = nearest_street(c)
    best = None; n = len(b["p"])
    for i in range(n):
        a, e = b["p"][i], b["p"][(i + 1) % n]
        mx, mz = (a[0] + e[0]) / 2, (a[1] + e[1]) / 2; dd = math.hypot(mx - q[0], mz - q[1]); ln = math.hypot(e[0] - a[0], e[1] - a[1])
        sc = dd - min(ln, 14) * 0.6
        if ln > 3 and (best is None or sc < best[0]): best = (sc, mx, mz, e[0] - a[0], e[1] - a[1], ln)
    _, mx, mz, ex, ez, ln = best
    nx, nz = ez / ln, -ex / ln
    if (mx + nx - c[0]) ** 2 + (mz + nz - c[1]) ** 2 < (mx - c[0]) ** 2 + (mz - c[1]) ** 2: nx, nz = -nx, -nz
    return {"x": r1(mx + nx * 1.4), "z": r1(mz + nz * 1.4), "wx": r1(mx), "wz": r1(mz), "nx": round(nx, 3), "nz": round(nz, 3)}
def street_spot(pt, side=1):
    d, q, ang = nearest_street(pt)
    return {"x": r1(q[0] - math.sin(ang) * 2.3 * side), "z": r1(q[1] + math.cos(ang) * 2.3 * side), "a": round(ang, 3)}

nadr_pt = L((-754403, -1041778)); nam_pt = L((-754614, -1042166)); zam_pt = L((-754666, -1042168))
i_nadr = building_near(nadr_pt, 150)
i_zam = building_near(zam_pt, 300)
i_hosp = building_near((nam_pt[0] + 62, nam_pt[1] + 10), 110, 700, (i_zam,))
i_vec = building_near((nam_pt[0] - 5, nam_pt[1] - 95), 110, 900, (i_zam, i_hosp))
i_dil = building_near((667, 440), 300, 5000, (i_zam, i_hosp, i_vec))
for i, n in ((i_nadr, "NÁDRAŽÍ HOSTIVICE"), (i_zam, "ZÁMEK · MĚSTSKÝ ÚŘAD"), (i_hosp, "HOSPODA NA NÁMĚSTÍ"), (i_vec, "VEČERKA"), (i_dil, "AUTODÍLNA")):
    budovy[i]["n"] = n; budovy[i]["d"] = door(i)
pk = min(parkoviste, key=lambda p: math.hypot(centroid(p)[0] - zam_pt[0], centroid(p)[1] - zam_pt[1]))
pkc = centroid(pk)
dS = nearest_street(nadr_pt)
mista = {
    "start": {"x": r1(budovy[i_nadr]["d"]["x"]), "z": r1(budovy[i_nadr]["d"]["z"])},
    "hospoda": {"x": budovy[i_hosp]["d"]["x"], "z": budovy[i_hosp]["d"]["z"]},
    "vecerka": {"x": budovy[i_vec]["d"]["x"], "z": budovy[i_vec]["d"]["z"]},
    "predHospodou": street_spot((budovy[i_hosp]["d"]["x"], budovy[i_hosp]["d"]["z"])),
    "dilna": street_spot((budovy[i_dil]["d"]["x"], budovy[i_dil]["d"]["z"])),
    "felicita": street_spot((215, 468)),
    "dodavka": street_spot((budovy[i_vec]["d"]["x"], budovy[i_vec]["d"]["z"])),
    "manazerak": street_spot((640, 660)),
    "balik1": street_spot((140, 250)), "balik2": street_spot((575, 335)), "balik3": street_spot((440, 765)),
    "namesti": {"x": r1(nam_pt[0]), "z": r1(nam_pt[1])},
}

world = {
    "n": N, "g": G, "hmin": round(hmin, 2),
    "ter": base64.b64encode(np.round(grid * 100).astype("<u2").tobytes()).decode(),
    "budovy": budovy, "ulice": ulice, "trat": trat, "voda": voda, "stromy": stromy, "lampy": lampy, "mista": mista,
}
(OUT / "world.json").write_text(json.dumps(world, separators=(",", ":"), ensure_ascii=False))
ortho = Image.open(SRC / "ortho.png").convert("RGB")
ortho.resize((2560, 2560), Image.LANCZOS).save(OUT / "ortho.jpg", quality=80, optimize=True)
print("budov", len(budovy), "typy", [sum(b["t"] == t for b in budovy) for t in (0, 1, 2)], "stromů", len(stromy), "lamp", len(lampy), "ulic", len(ulice))
print("výšky terénu", round(float(ter.max()), 1), "m; world.json", (OUT / "world.json").stat().st_size // 1024, "kB; ortho", (OUT / "ortho.jpg").stat().st_size // 1024, "kB")

# kontrolní obrázek
dbg = ortho.resize((1600, 1600)); d = ImageDraw.Draw(dbg); k = 2
for b in budovy: d.polygon([(x * k, z * k) for x, z in b["p"]], outline=(255, 255, 0) if b["t"] == 1 else (0, 255, 255) if b["t"] == 2 else (255, 0, 255))
for s in ulice: d.line([(x * k, z * k) for x, z in s["p"]], fill=(255, 255, 255) if s["a"] else (160, 160, 160), width=2)
for x, z, h in stromy: d.ellipse((x * k - 3, z * k - 3, x * k + 3, z * k + 3), outline=(0, 255, 0))
for n, m in mista.items():
    d.ellipse((m["x"] * k - 8, m["z"] * k - 8, m["x"] * k + 8, m["z"] * k + 8), fill=(255, 60, 60)); d.text((m["x"] * k + 10, m["z"] * k - 6), n, fill=(255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0))
dbg.save(SRC / "debug.jpg", quality=80)
