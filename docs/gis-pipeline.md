# GIS pipeline: reálná Hostivice do UE5

Souřadnicový systém projektu je **UTM 33N (EPSG:32633)**. Vše z ČÚZK přichází
v S-JTSK (EPSG:5514) a musí se převést. Počátek světa UE = střed výřezu
(Husovo náměstí); jeho UTM souřadnice vypíše exportní skript.

## 1. Zdroje dat

| Data | Zdroj | K čemu |
|---|---|---|
| DMR 5G | Geoportál ČÚZK | terén bez budov → heightmapa |
| DMP 1G | Geoportál ČÚZK | povrch s budovami a stromy → výšky budov |
| Ortofoto ČR | Geoportál ČÚZK | kontrola měřítka, podklad pro materiály |
| RÚIAN | ČÚZK (VFR nebo WFS) | přesné půdorysy budov |
| OpenStreetMap | Geofabrik / Overpass | silnice, chodníky, landuse, zastávky |

Stažená data ukládejte do `tools/gis/data/` (je v `.gitignore`).

## 2. Heightmapa

Doporučená cesta, bez registrace a bez GDAL:

```bash
pip install rasterio pyproj numpy pillow
python3 tools/gis/fetch_cuzk.py
```

Skript stáhne DMR 5G a DMP 1G z veřejné služby ČÚZK (ArcGIS ImageServer),
převede je do UTM 33N a do `tools/gis/out/` uloží:

| Soubor | Obsah |
|---|---|
| `hostivice_height.png` | 16bit heightmapa terénu, 8129 × 8129 px, 1 m/px |
| `hostivice_objects.tif` | výška budov a stromů nad terénem (DMP − DMR) v metrech |
| `hostivice_hillshade.png` | stínovaný náhled pro kontrolu |
| `landscape_params.txt` | Scale Z, Location Z a počátek světa pro UE |

Služba má nativní krok 2 m, výstup 1 m/px je převzorkovaný. Pro terén to
stačí; ostré hrany (náspy trati, hráze rybníků) se doladí ručně v editoru.

Střed výřezu se mění parametry `--lon` a `--lat`. Výchozí hodnota je
přibližná poloha Husova náměstí – ověřte ji nad ortofotem.

Alternativa pro vlastní GeoTIFFy stažené z Geoportálu: `export_heightmap.sh`
(vyžaduje GDAL).

## 3. Import do UE5

1. Nová mapa typu **Open World** (World Partition zapnutý).
2. Landscape Mode → Import from File → `hostivice_height.png`.
3. Scale X/Y = 100, Scale Z a Location Z podle `landscape_params.txt`.
4. Section Size 127×127, 2×2 sekce na komponentu.
5. **Kontrola měřítka:** ortofoto jako dočasný materiál, změřit známou
   vzdálenost (např. délku nádražní budovy) nástrojem pro měření ve viewportu
   (prostřední tlačítko myši v ortografickém pohledu).

## 4. Blockout budov (Blender)

1. Blosm: import budov a silnic pro stejný výřez.
2. Půdorysy nahradit nebo zpřesnit podle RÚIAN (import GeoJSON/SHP v UTM 33N).
3. Výška budovy = medián rastru `hostivice_objects.tif` uvnitř půdorysu. Spočítá
   QGIS nástroj *Zonal Statistics*; výsledek se uloží jako atribut `height`.
4. Extrude podle `height`. Origin scény = počátek světa z kroku 2.
5. Export FBX po blocích zhruba 250 × 250 m, v UE zapnout Nanite.

## 5. Silnice

OSM `highway=*` → spline. Pro slice stačí ručně obtáhnout Landscape Splines
podle ortofota: Čsl. armády, Husovo náměstí, příjezd k nádraží. Stejné spliny
později poslouží jako zdroj pro ZoneGraph (jízdní pruhy pro Mass provoz).
