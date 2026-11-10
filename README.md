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
| `tools/gis/` | Export heightmapy z dat ČÚZK. |
| `docs/GDD.md` | Game design document. |
| `docs/gis-pipeline.md` | Postup importu reálné mapy. |

## Jak začít

1. Nainstalovat UE 5.5+, Visual Studio 2022 a Git LFS (`git lfs install`).
2. Pravým tlačítkem na `.uproject` → *Generate Visual Studio project files*.
3. Otevřít `.uproject` a nechat zkompilovat moduly.
4. Pokračovat podle `docs/gis-pipeline.md`.
