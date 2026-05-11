# Energia Szimulációs Projekt

Ez a projekt egy energiafogyasztási és napelemes termelési szimulátor 2026-ra, amely különböző háztípusokat modellez Magyarországon.

## Fájlok és Mire Valók

- **generator.py**: A fő szimulációs szkript. Generálja a házak energiaadatait (fogyasztás, termelés, nettó hálózati forgalom) és menti CSV-ként a `haz_adatok/` mappába. 6 különböző háztípust szimulál: idős, család, egyedülálló, néhányukkal napelemes rendszerrel.

- **WS.py**: Időjárás-szimulátor osztály. Számítja ki a napelemes tényezőket idő alapján, figyelembe véve a szezonális változásokat, felhősödést és rossz időjárási körülményeket.

- **HP.py**: Házprofilok osztálya. Definiálja a különböző életmódbeli fogyasztási mintákat óránként (pl. idős: korai kelés, család: esti nagyüzem).

- **visual.py**: Vizualizációs szkript. Éves grafikonokat készít egy ház fogyasztásáról, napelemes termeléséről és hálózati egyenlegről. PNG képet ment.

- **dayvisual.py**: Napi vizualizáció. Véletlenszerű vagy adott nap részletes grafikonját készíti, fogyasztással, termeléssel és nettó forgalommal.

- **haz_adatok/**: Mappa a generált CSV fájloknak (Haz_1_Idos.csv stb.), amelyek 15 perces energiaadatokat tartalmaznak 2026 egész évére.

## Hogyan Futtasd

1. Győződj meg róla, hogy telepítve van Python és a szükséges könyvtárak: `pandas`, `numpy`, `matplotlib`.

2. Futtasd a generátort: `python generator.py` – Ez létrehozza a CSV fájlokat.

3. Vizualizáláshoz: `python visual.py` (éves grafikon) vagy `python dayvisual.py` (napi grafikon).

## Cél

Mock adatok előállítása energiaelemzésekhez, napelemes rendszerek szimulációjához vagy kutatáshoz.

---

## Konténerizált webhook-streamer

A `webhook.py` egy kis FastAPI szolgáltatást indít, amely a
`haz_adatok/osszes_haz_adat.csv` tartalmát továbbítja az
energy-community backend `/webhook/powermocker` végpontjára,
naponta egy adag (batch) felbontásban. Konténerként, a fő alkalmazás
mellett futtatható közös Podman hálózaton:

```bash
# az energy_community repo gyökeréből (közös hálózat egyszeri létrehozása)
podman network create energy-net
podman compose up --build                                    # db + backend + frontend

# ebből a könyvtárból
podman compose up --build                                    # powermocker a 9000-es porton
```

### Végpontok

| Metódus | Útvonal  | Test                                                 | Leírás                                                  |
|---------|----------|------------------------------------------------------|---------------------------------------------------------|
| POST    | `/start` | `{ "days": 30, "delay_ms": 500, "drop_first": true }`| Háttérszálon elindítja az adatküldést (202).            |
| POST    | `/stop`  | —                                                    | Megszakítja a folyamatban lévő küldést.                 |
| GET    | `/status`| —                                                    | `{ running, current_day, total_days, sent, ... }`.      |
| GET    | `/health`| —                                                    | Életjelzés + feloldott backend- és CSV-útvonalak.       |

A `days: 0` (alapértelmezett) az egész CSV-t küldi. A `delay_ms` a napi
adagok közötti szünet (576 sor = 6 ház × 96 negyedóra).

### Környezeti változók

| Változó                | Alapérték                                          |
|------------------------|----------------------------------------------------|
| `BACKEND_WEBHOOK_URL`  | `http://backend:8000/webhook/powermocker`          |
| `POWERMOCKER_CSV`      | `./haz_adatok/osszes_haz_adat.csv`                 |

### Gyors indítás

```bash
curl -X POST http://localhost:9000/start \
     -H 'Content-Type: application/json' \
     -d '{"days": 30, "delay_ms": 500, "drop_first": true}'
```