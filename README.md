# Hostivice: Za čárou

Open-world akční hra zasazená do reálné Hostivice u Prahy. Unreal Engine 5.5+.

## Stav

Milník M0: kostra projektu. Zatím bez assetů a map; kód ještě nebyl
zkompilován v editoru.

## Struktura

| Cesta | Obsah |
|---|---|
| `HostiviceZaCarou.uproject` | Projekt, zapnuté pluginy (Chaos Vehicles, GAS, Mass, PCG, Water…). |
| `Config/` | Lumen s HW ray tracingem, Nanite, Virtual Shadow Maps, DX12. |
| `Source/HostiviceCore` | Sdílený základ, rozhraní `IHostiviceInteractable`. |
| `Source/HostiviceVehicles` | `AHostiviceVehicleBase` – řízení, palivo, poškození, nastupování. |
| `Source/HostiviceAI` | Chodci, provoz, policie (zatím prázdný modul). |
| `Source/HostiviceWorld` | Den/noc, počasí, interiéry (zatím prázdný modul). |
| `Source/HostiviceMissions` | Mise a frakce (zatím prázdný modul). |
| `tools/gis/` | Stažení a zpracování dat ČÚZK (terén, ortofoto, budovy, ulice). |
| `data/terrain/` | Heightmapa 8129 × 8129 px pro UE Landscape a parametry importu. |
| `prototype/hostivice-3d.html` | Hratelná 3D ukázka skutečné Hostivice v prohlížeči (three.js). |
| `prototype/za-carou-2d.html` | Starší schematická 2D ukázka herních mechanik. |
| `docs/GDD.md` | Game design document. |
| `docs/gis-pipeline.md` | Postup importu reálné mapy. |

## Jak začít

1. Nainstalovat UE 5.5+, Visual Studio 2022 a Git LFS (`git lfs install`).
2. Pravým tlačítkem na `.uproject` → *Generate Visual Studio project files*.
3. Otevřít `.uproject` a nechat zkompilovat moduly.
4. Pokračovat podle `docs/gis-pipeline.md`.

## 3D ukázka v prohlížeči

Výřez 800 × 800 m kolem Husova náměstí a nádraží. Data se připraví dvěma skripty:

```bash
python3 tools/gis/fetch_slice3d.py   # stáhne ortofoto, DMR 5G, DMP 1G, RÚIAN a ZABAGED
python3 tools/gis/build_slice3d.py   # vyrobí prototype/hostivice3d/world.json a ortho.jpg
```

Stránku je potřeba otevřít přes webový server (`python3 -m http.server` ve složce
`prototype/`), ne jako soubor z disku.

Podkladová data © ČÚZK, otevřená data.
