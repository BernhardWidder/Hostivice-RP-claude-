#!/usr/bin/env bash
# Export heightmapy Hostivice pro UE5 Landscape.
#
# Vstup:  jeden nebo více GeoTIFFů DMR 5G (S-JTSK, EPSG:5514).
#         ČÚZK dodává DMR 5G i jako mračna bodů LAZ – ta nejdřív zrastrujte
#         na GeoTIFF s krokem 1 m (PDAL writers.gdal nebo QGIS > Processing).
# Výstup: out/hostivice_height.png  – 16bit PNG, 8129 × 8129 px, 1 m/px, UTM 33N
#         out/landscape_params.txt  – hodnoty pro dialog Import Landscape
#
# Použití: ./export_heightmap.sh data/dmr5g_*.tif
# Vyžaduje: GDAL >= 3.4 (gdalwarp, gdal_translate, gdalinfo, gdaltransform), python3

set -euo pipefail

# Střed výřezu: Husovo náměstí (WGS84). PŘIBLIŽNÁ hodnota – před prvním
# exportem ji ověřte v QGIS nad ortofotem a případně přepište.
CENTER_LON="${CENTER_LON:-14.2586}"
CENTER_LAT="${CENTER_LAT:-50.0817}"

# 8129 px je doporučená velikost UE Landscape; při 1 m/px pokryje 8,1 × 8,1 km.
SIZE_PX=8129

if [ "$#" -lt 1 ]; then
	echo "Použití: $0 <dmr5g.tif> [další.tif ...]" >&2
	exit 1
fi

OUT_DIR="$(dirname "$0")/out"
mkdir -p "$OUT_DIR"

# Střed do UTM 33N, zaokrouhlený na celé metry kvůli zarovnání pixelů.
read -r CX CY _ < <(echo "$CENTER_LON $CENTER_LAT" | gdaltransform -s_srs EPSG:4326 -t_srs EPSG:32633)
CX=$(printf '%.0f' "$CX")
CY=$(printf '%.0f' "$CY")

read -r XMIN YMIN XMAX YMAX < <(python3 - "$CX" "$CY" "$SIZE_PX" <<'PY'
import sys
cx, cy, n = float(sys.argv[1]), float(sys.argv[2]), int(sys.argv[3])
h = n / 2.0
print(cx - h, cy - h, cx + h, cy + h)
PY
)

echo "Střed UTM 33N: $CX $CY"
echo "Výřez: $XMIN $YMIN $XMAX $YMAX"

# 1) Reprojekce S-JTSK -> UTM 33N, ořez, převzorkování na 1 m.
gdalwarp -overwrite \
	-s_srs EPSG:5514 -t_srs EPSG:32633 \
	-te "$XMIN" "$YMIN" "$XMAX" "$YMAX" \
	-ts "$SIZE_PX" "$SIZE_PX" \
	-r bilinear -ot Float32 -dstnodata -9999 \
	"$@" "$OUT_DIR/dmr_utm33.tif"

# 2) Skutečný rozsah výšek ve výřezu.
read -r ZMIN ZMAX < <(gdalinfo -mm "$OUT_DIR/dmr_utm33.tif" \
	| sed -n 's/.*Computed Min\/Max=\([-0-9.]*\),\([-0-9.]*\).*/\1 \2/p')

if [ -z "${ZMIN:-}" ] || [ -z "${ZMAX:-}" ]; then
	echo "Nepodařilo se zjistit rozsah výšek – pokrývají vstupní data celý výřez?" >&2
	exit 1
fi

# 3) Roztažení na celý 16bit rozsah.
gdal_translate -of PNG -ot UInt16 \
	-scale "$ZMIN" "$ZMAX" 0 65535 -a_nodata none \
	"$OUT_DIR/dmr_utm33.tif" "$OUT_DIR/hostivice_height.png"

# 4) Parametry pro UE. Landscape mapuje 16 bitů na 512 m při Z scale 100.
python3 - "$ZMIN" "$ZMAX" "$CX" "$CY" > "$OUT_DIR/landscape_params.txt" <<'PY'
import sys
zmin, zmax, cx, cy = map(float, sys.argv[1:5])
rng = zmax - zmin
print(f"Rozsah výšek:        {zmin:.2f} – {zmax:.2f} m n. m. ({rng:.2f} m)")
print(f"Landscape Scale X/Y: 100")
print(f"Landscape Scale Z:   {rng / 512.0 * 100.0:.4f}")
print(f"Landscape Location Z:{(zmin + zmax) / 2.0 * 100.0:.1f} cm  (aby Z = nadmořská výška)")
print(f"Počátek světa (UTM): E {cx:.0f}, N {cy:.0f}  -> stejný origin použijte v Blenderu")
PY

cat "$OUT_DIR/landscape_params.txt"
