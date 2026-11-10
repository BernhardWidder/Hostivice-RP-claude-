# Hostivice: Za čárou – Game Design Document (v0.1)

## 1. Vize

Open-world akční hra z pohledu třetí osoby zasazená do reálné Hostivice u Prahy.
Hrdina se vrací do rodného města s dluhy a zděděným rozpadlým domkem v Litovicích.
Město sevřené mezi Prahou, letištěm Ruzyně, dálnicí D6 a logistickými halami je
ideální překladiště pro pašování, kradená auta a developerské podvody.

### Pilíře

| Pilíř | Co znamená v praxi |
|---|---|
| Hustota místo rozlohy | Každá hospoda, dvorek a průchod má herní účel. Žádná prázdná mapa. |
| Tři frakce | Reputace u jedné mění přístup k misím, cenám i reakce NPC ostatních. |
| Česká autenticita | Hospoda jako hub, večerka, osobák do Prahy, autobusy, městská vs. státní policie. |

### Frakce

1. **Staří psi** – štamgasti, veteráni, pašeráci z garáží. Hub: hospoda na náměstí.
2. **Pražský organizovaný zločin** – luxusní kradená auta, cargo z letiště.
3. **Developerská klika** – zkorumpovaní politici a developeři, kteří chtějí zastavět rybníky a historické jádro.

### Názvy a značky

Reálné firmy, loga a značky aut ve hře nebudou. Vozy dostanou parodické názvy
(pracovně „Felicita" pro první auto), obchody smyšlená jména. Veřejné budovy
a uliční síť zůstávají podle skutečnosti.

## 2. Vertical slice (500 × 500 m)

Okolí Husova náměstí. Cíl: ověřit všechny klíčové systémy na malé ploše, než se
začne stavět zbytek katastru (14,5 km²).

| Místo | Role |
|---|---|
| Nádraží Hostivice | Start hry, příjezd osobním vlakem z Prahy. |
| Hospoda „Na Náměstí" | Hub Starých psů: mise, drby, pivo doplňuje zdraví. Enterable interiér. |
| Večerka u náměstí | Nákup jídla a drobností, zboží pod pultem po získání reputace. |
| Zámek a park | Úřad a městská policie. Později cíl infiltračních misí. |

### Mise 01: Návrat do Litovic

1. Hráč vystoupí z vlaku na nádraží. Krátký úvod, SMS od věřitele.
2. Pěšky ulicí Čsl. armády na náměstí (výuka pohybu, vaultování přes zábradlí).
3. Vstup do hospody bez loadingu, rozhovor s mechanikem.
4. Mechanik půjčí starou Felicitu zaparkovanou za zámeckým parkem.
5. Jízda provozem zpět k hospodě. Konec slice.

**Co mise testuje:** Motion Matching, streamování interiéru, dialogy, interakce
(`IHostiviceInteractable`), nastupování do auta, Chaos Vehicles, Mass provoz.

### Hotovo znamená

- 60 fps v 1440p na RTX 3070 s Lumen HWRT.
- Průchod misí bez jediné načítací obrazovky.
- Minimálně 30 chodců a 15 aut v dohledu přes Mass.
- Blockout budov odpovídá RÚIAN s odchylkou do 1 m.

## 3. Art direction slice

- **Náměstí a zámek:** jediná lokace s fotogrammetrií (RealityScan). Zbytek modulární kity.
- **Kit „český rodinný dům":** břízolit, eternit, plastová okna vedle špaletových, podezdívky plotů.
- **Mobiliář:** zastávka PID, žluté popelnice, výlepová plocha, zámková dlažba, české značky.
- **Hospoda:** výčep, lakované stoly, automaty, zažloutlé stěny, zářivka nad barem a teplé žárovky u stolů.
- **Světlo:** první mise za podzimního podvečera – nízké slunce, mokrý asfalt, rozsvěcující se lampy.
- **Zvuk:** letadla na přistání nad městem, osobní vlak, kostelní zvon.

## 4. Milníky

| # | Milník | Výstup |
|---|---|---|
| M0 | Základ projektu | Kompilující projekt, moduly, Git LFS. |
| M1 | Terén 1:1 | Landscape z DMR 5G, ověřené měřítko. Viz `docs/gis-pipeline.md`. |
| M2 | Blockout slice | Budovy z RÚIAN, silnice z OSM, šedé boxy. |
| M3 | Postava a auto | Motion Matching postava, jedno řiditelné auto, nastupování. |
| M4 | Interiér | Hospoda streamovaná jako Level Instance. |
| M5 | Život | Mass chodci a provoz na ZoneGraph. |
| M6 | Mise 01 | Hratelná od vlaku po návrat k hospodě. |
