#!/usr/bin/env python3
"""Stáhne podklady pro 3D ukázku okolí Husova náměstí (800 × 800 m) z ČÚZK.

Výstup do tools/gis/data/slice3d/: ortofoto, DMR 5G, DMP 1G (1 m/px) a vektorové
vrstvy RÚIAN/ZABAGED jako JSON. Vše v S-JTSK (EPSG:5514).

Použití: python3 fetch_slice3d.py
"""
import io, json, time, urllib.parse, urllib.request
from pathlib import Path
import numpy as np, rasterio
from PIL import Image

X0, X1, Y0, Y1 = -754950, -754150, -1042400, -1041600   # výřez S-JTSK
OUT = Path(__file__).parent / "data" / "slice3d"
AGS = "https://ags.cuzk.cz"
UA = {"User-Agent": "gis-export-script/0.1"}


def get(url, params, tries=5):
    full = url + "?" + urllib.parse.urlencode(params)
    err = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(full, headers=UA), timeout=150) as r:
                return r.read()
        except Exception as e:
            err = e; time.sleep(2 ** (i + 1))
    raise RuntimeError(f"{url}: {err}")


def ortho(px_per_m=4, tile_m=200):
    n = int((X1 - X0) * px_per_m)
    img = Image.new("RGB", (n, n))
    for ty in range(0, Y1 - Y0, tile_m):
        for tx in range(0, X1 - X0, tile_m):
            bbox = f"{X0 + tx},{Y1 - ty - tile_m},{X0 + tx + tile_m},{Y1 - ty}"
            data = get(f"{AGS}/arcgis1/rest/services/ORTOFOTO/MapServer/export", {
                "bbox": bbox, "bboxSR": 5514, "imageSR": 5514, "size": f"{tile_m * px_per_m},{tile_m * px_per_m}",
                "format": "png24", "f": "image"})
            img.paste(Image.open(io.BytesIO(data)).convert("RGB"), (tx * px_per_m, ty * px_per_m))
            print("ortofoto", tx, ty, flush=True)
    img.save(OUT / "ortho.png")


def raster(name):
    w, h = X1 - X0, Y1 - Y0
    out = np.zeros((h, w), np.float32)
    step = 400
    for ty in range(0, h, step):
        for tx in range(0, w, step):
            data = get(f"{AGS}/arcgis2/rest/services/{name}/ImageServer/exportImage", {
                "bbox": f"{X0 + tx},{Y1 - ty - step},{X0 + tx + step},{Y1 - ty}", "bboxSR": 5514, "imageSR": 5514,
                "size": f"{step},{step}", "format": "tiff", "pixelType": "F32", "compression": "LZW",
                "interpolation": "RSP_BilinearInterpolation", "f": "image"})
            with rasterio.open(io.BytesIO(data)) as ds:
                out[ty:ty + step, tx:tx + step] = ds.read(1)
            print(name, tx, ty, flush=True)
    np.save(OUT / f"{name}.npy", out)


def layer(service, lid, name):
    feats, offset = [], 0
    while True:
        d = json.loads(get(f"{AGS}/arcgis/rest/services/{service}/MapServer/{lid}/query", {
            "geometry": f"{X0},{Y0},{X1},{Y1}", "geometryType": "esriGeometryEnvelope", "inSR": 5514, "outSR": 5514,
            "spatialRel": "esriSpatialRelIntersects", "outFields": "*", "returnGeometry": "true",
            "resultOffset": offset, "resultRecordCount": 1000, "f": "json"}))
        if "error" in d: raise RuntimeError(f"{name}: {d['error']}")
        feats += d.get("features", [])
        if not d.get("exceededTransferLimit"): break
        offset += 1000
    (OUT / f"{name}.json").write_text(json.dumps(feats))
    print(name, len(feats), flush=True)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    layer("RUIAN", 3, "budovy")
    layer("ZABAGED_POLOHOPIS", 84, "ulice")
    layer("ZABAGED_POLOHOPIS", 79, "silnice")
    layer("ZABAGED_POLOHOPIS", 83, "cesty")
    layer("ZABAGED_POLOHOPIS", 75, "trat")
    layer("ZABAGED_POLOHOPIS", 132, "voda")
    layer("ZABAGED_POLOHOPIS", 123, "parkoviste")
    raster("dmr5g"); raster("dmp1g")
    ortho()
