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

## Container + Webhook Streamer

`webhook.py` exposes a small FastAPI service that replays
`haz_adatok/osszes_haz_adat.csv` to the energy-community backend's
`/webhook/powermocker` endpoint, one day-batch at a time. Run it as a
container alongside the main app on a shared Podman network:

```bash
# from the energy_community repo root (creates the shared network once)
podman network create energy-net
podman compose up --build                                    # db + backend + frontend

# from this directory
podman compose up --build                                    # powermocker on :9000
```

### Endpoints

| Method | Path     | Body                                                 | Description                                        |
|--------|----------|------------------------------------------------------|----------------------------------------------------|
| POST   | `/start` | `{ "days": 30, "delay_ms": 500, "drop_first": true }`| Kicks off streaming in a background thread (202).  |
| POST   | `/stop`  | —                                                    | Cancels an in-flight stream.                       |
| GET    | `/status`| —                                                    | `{ running, current_day, total_days, sent, ... }`. |
| GET    | `/health`| —                                                    | Liveness probe + resolved backend/CSV paths.       |

`days: 0` (default) streams the whole CSV. `delay_ms` is the pause between
day-batches (576 rows = 6 houses × 96 quarter-hours).

### Environment

| Variable               | Default                                            |
|------------------------|----------------------------------------------------|
| `BACKEND_WEBHOOK_URL`  | `http://backend:8000/webhook/powermocker`          |
| `POWERMOCKER_CSV`      | `./haz_adatok/osszes_haz_adat.csv`                 |

### Quick trigger

```bash
curl -X POST http://localhost:9000/start \
     -H 'Content-Type: application/json' \
     -d '{"days": 30, "delay_ms": 500, "drop_first": true}'
```