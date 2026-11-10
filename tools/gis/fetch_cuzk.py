#!/usr/bin/env python3
"""Stáhne výškopis Hostivice z ČÚZK a připraví podklady pro UE5.

Nevyžaduje registraci ani GDAL – data bere z veřejné služby ArcGIS ImageServer
(https://ags.cuzk.cz/arcgis2/rest/services), kterou ČÚZK poskytuje jako open data.

Výstupy (složka out/):
  hostivice_height.png      16bit heightmapa terénu (DMR 5G), 8129 × 8129 px, 1 m/px, UTM 33N
  hostivice_objects.tif     výška objektů nad terénem (DMP 1G − DMR 5G) v metrech, Float32
  hostivice_hillshade.png   stínovaný náhled terénu pro rychlou kontrolu
  landscape_params.txt      hodnoty pro dialog Import Landscape

Služba má nativní krok 2 m; výstup 1 m/px je bilineárně převzorkovaný.

Instalace: pip install rasterio pyproj numpy pillow
Použití:   python3 fetch_cuzk.py [--lon 14.2586 --lat 50.0817]
"""

from __future__ import annotations

import argparse
import io
from concurrent.futures import ThreadPoolExecutor
import math
import time
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image
from pyproj import Transformer
from rasterio.crs import CRS
from rasterio.transform import from_origin
from rasterio.warp import Resampling, reproject

SERVICE = "https://ags.cuzk.cz/arcgis2/rest/services/{name}/ImageServer/exportImage"
SIZE_PX = 8129          # doporučená velikost UE Landscape
NATIVE_STEP = 2.0       # nativní krok rastru služby v metrech
TILE_PX = 500           # dlaždice 1 × 1 km; větší služba posílá příliš pomalu
WORKERS = 6             # počet souběžných stahování
NODATA = -9999.0
SJTSK = CRS.from_epsg(5514)
UTM33 = CRS.from_epsg(32633)


def fetch_tile(name: str, cache: Path, xmin: float, ymin: float, xmax: float, ymax: float,
               w: int, h: int) -> np.ndarray:
    """Jedna dlaždice ze služby jako Float32 pole (řádek 0 = sever).

    Stažené dlaždice se ukládají do cache, takže přerušený běh naváže tam, kde skončil.
    """
    cached = cache / f"{name}_{xmin:.0f}_{ymin:.0f}_{w}x{h}.tif"
    if cached.exists():
        with rasterio.open(cached) as dataset:
            return dataset.read(1).astype(np.float32)

    query = urllib.parse.urlencode({
        "bbox": f"{xmin},{ymin},{xmax},{ymax}",
        "bboxSR": 5514,
        "imageSR": 5514,
        "size": f"{w},{h}",
        "format": "tiff",
        "pixelType": "F32",
        "compression": "LZW",
        "noData": NODATA,
        "interpolation": "RSP_BilinearInterpolation",
        "f": "image",
    })
    url = SERVICE.format(name=name) + "?" + query
    request = urllib.request.Request(url, headers={"User-Agent": "gis-export-script/0.1"})

    last_error: Exception | None = None
    for attempt in range(5):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                payload = response.read()
            with rasterio.open(io.BytesIO(payload)) as dataset:
                data = dataset.read(1).astype(np.float32)
            if data.shape != (h, w):
                raise ValueError(f"služba vrátila {data.shape}, čekáno {(h, w)}")
            cached.write_bytes(payload)
            return data
        except Exception as error:  # síť i poškozená odpověď: zkusit znovu
            last_error = error
            time.sleep(2 ** (attempt + 1))
    raise RuntimeError(f"Dlaždici {name} se nepodařilo stáhnout: {last_error}")


def fetch_mosaic(name: str, bounds: tuple[float, float, float, float],
                 cache: Path) -> tuple[np.ndarray, rasterio.Affine]:
    """Stáhne celý výřez v S-JTSK po dlaždicích a složí ho do jednoho rastru."""
    xmin, ymin, xmax, ymax = bounds
    width = int(round((xmax - xmin) / NATIVE_STEP))
    height = int(round((ymax - ymin) / NATIVE_STEP))
    mosaic = np.full((height, width), NODATA, dtype=np.float32)

    jobs = []
    for row in range(0, height, TILE_PX):
        for col in range(0, width, TILE_PX):
            jobs.append((row, col, min(TILE_PX, width - col), min(TILE_PX, height - row)))

    def run(job: tuple[int, int, int, int]) -> tuple[int, int, np.ndarray]:
        row, col, w, h = job
        tx0 = xmin + col * NATIVE_STEP
        ty1 = ymax - row * NATIVE_STEP
        return row, col, fetch_tile(name, cache, tx0, ty1 - h * NATIVE_STEP, tx0 + w * NATIVE_STEP, ty1, w, h)

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for done, (row, col, data) in enumerate(pool.map(run, jobs), start=1):
            mosaic[row:row + data.shape[0], col:col + data.shape[1]] = data
            if done % 10 == 0 or done == len(jobs):
                print(f"  {name}: dlaždice {done}/{len(jobs)}", flush=True)

    return mosaic, from_origin(xmin, ymax, NATIVE_STEP, NATIVE_STEP)


def warp_to_utm(source: np.ndarray, source_transform: rasterio.Affine,
                cx: float, cy: float) -> tuple[np.ndarray, rasterio.Affine]:
    """Reprojekce S-JTSK -> UTM 33N na mřížku 8129 × 8129 px po 1 m se středem cx, cy."""
    half = SIZE_PX / 2.0
    target_transform = from_origin(cx - half, cy + half, 1.0, 1.0)
    target = np.full((SIZE_PX, SIZE_PX), NODATA, dtype=np.float32)
    reproject(
        source, target,
        src_transform=source_transform, src_crs=SJTSK, src_nodata=NODATA,
        dst_transform=target_transform, dst_crs=UTM33, dst_nodata=NODATA,
        resampling=Resampling.bilinear,
    )
    return target, target_transform


def hillshade(height: np.ndarray, azimuth: float = 315.0, altitude: float = 40.0) -> np.ndarray:
    dy, dx = np.gradient(height.astype(np.float64))
    slope = np.pi / 2.0 - np.arctan(np.hypot(dx, dy) * 2.0)   # 2× převýšení pro čitelnost
    aspect = np.arctan2(-dx, dy)
    az, alt = np.radians(azimuth), np.radians(altitude)
    shaded = np.sin(alt) * np.sin(slope) + np.cos(alt) * np.cos(slope) * np.cos(az - aspect)
    return (np.clip(shaded, 0.0, 1.0) * 255).astype(np.uint8)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--lon", type=float, default=14.2586, help="zeměpisná délka středu (WGS84)")
    parser.add_argument("--lat", type=float, default=50.0817, help="zeměpisná šířka středu (WGS84)")
    parser.add_argument("--out", type=Path, default=Path(__file__).parent / "out")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    cache = Path(__file__).parent / "data" / "tiles"
    cache.mkdir(parents=True, exist_ok=True)

    # Střed v UTM 33N zaokrouhlený na celé metry = počátek světa v UE.
    cx, cy = Transformer.from_crs(4326, UTM33, always_xy=True).transform(args.lon, args.lat)
    cx, cy = round(cx), round(cy)
    half = SIZE_PX / 2.0

    # Obálka výřezu v S-JTSK. Osy S-JTSK jsou vůči UTM pootočené, proto bereme
    # obálku z hustě navzorkovaného obvodu a přidáváme 20 m rezervu.
    to_sjtsk = Transformer.from_crs(UTM33, SJTSK, always_xy=True)
    edge = np.linspace(-half, half, 65)
    px = np.concatenate([cx + edge, cx + edge, np.full(65, cx - half), np.full(65, cx + half)])
    py = np.concatenate([np.full(65, cy - half), np.full(65, cy + half), cy + edge, cy + edge])
    sx, sy = to_sjtsk.transform(px, py)
    snap = lambda value, fn: fn(value / NATIVE_STEP) * NATIVE_STEP
    bounds = (snap(min(sx) - 20, math.floor), snap(min(sy) - 20, math.floor),
              snap(max(sx) + 20, math.ceil), snap(max(sy) + 20, math.ceil))

    print(f"Střed UTM 33N: E {cx}, N {cy}")
    print(f"Obálka S-JTSK: {bounds}")

    terrain_src, src_transform = fetch_mosaic("dmr5g", bounds, cache)
    surface_src, _ = fetch_mosaic("dmp1g", bounds, cache)

    terrain, transform = warp_to_utm(terrain_src, src_transform, cx, cy)
    surface, _ = warp_to_utm(surface_src, src_transform, cx, cy)

    missing = int((terrain == NODATA).sum())
    if missing:
        raise SystemExit(f"DMR 5G má ve výřezu {missing} prázdných pixelů – heightmapa by měla díry.")

    zmin, zmax = float(terrain.min()), float(terrain.max())
    height16 = np.round((terrain - zmin) / (zmax - zmin) * 65535.0).astype(np.uint16)
    Image.fromarray(height16).save(args.out / "hostivice_height.png")
    Image.fromarray(hillshade(terrain)).save(args.out / "hostivice_hillshade.png")

    # Výška objektů nad terénem; záporné hodnoty a díry v DMP = 0.
    objects = np.where(surface == NODATA, 0.0, np.maximum(surface - terrain, 0.0)).astype(np.float32)
    with rasterio.open(args.out / "hostivice_objects.tif", "w", driver="GTiff", width=SIZE_PX, height=SIZE_PX,
                       count=1, dtype="float32", crs=UTM33, transform=transform, compress="deflate") as dataset:
        dataset.write(objects, 1)

    value_range = zmax - zmin
    params = "\n".join([
        f"Střed výřezu (WGS84):  {args.lat:.5f} N, {args.lon:.5f} E",
        f"Počátek světa (UTM 33N): E {cx}, N {cy}",
        f"Velikost:              {SIZE_PX} × {SIZE_PX} px, 1 m/px",
        f"Rozsah výšek:          {zmin:.2f} – {zmax:.2f} m n. m. ({value_range:.2f} m)",
        "Landscape Scale X/Y:   100",
        f"Landscape Scale Z:     {value_range / 512.0 * 100.0:.4f}",
        f"Landscape Location Z:  {(zmin + zmax) / 2.0 * 100.0:.1f} cm (aby Z = nadmořská výška)",
        f"Nejvyšší objekt:       {float(objects.max()):.1f} m nad terénem",
        "Zdroj dat:             © ČÚZK, DMR 5G a DMP 1G",
    ])
    (args.out / "landscape_params.txt").write_text(params + "\n", encoding="utf-8")
    print(params)


if __name__ == "__main__":
    main()
