# Military Aircraft Tracker

A Python-based tool that collects, stores, and visualizes live ADS-B data for military aircraft. It polls the ADS-B Exchange API on a configurable interval, writes timestamped records to daily CSV files, and produces an interactive Folium map with per-aircraft flight tracks, altitude coloring, and aircraft-type filtering.

---

## 📦 Features

- **Live collection** — polls the ADS-B Exchange API every minute (configurable) for up to 3 hours per run; restarts safely append to the same daily file
- **Daily CSV storage** — data is written to `data/YYYY-MM/YYYY-MM-DD.csv`; files roll over automatically at midnight
- **Spoofing / error filtering** — removes fixes that imply physically impossible speeds (> 1,500 kts from prior fix)
- **Callsign persistence** — callsigns and squawk codes are cached in memory and pre-loaded from all historical CSVs at startup so `UNK C/S` never overwrites a previously known callsign
- **Callsign backfill** — if a callsign is learned mid-session, all earlier `UNK C/S` rows for that hex in the current day's file are retroactively updated
- **Interactive flight map** — Folium map saved to `analysis/flight_map.html` with:
  - Per-segment altitude color gradient (orange → yellow → green → cyan → blue → purple → red)
  - Per-aircraft-type layer toggles in the LayerControl panel
  - Military base markers (toggleable, off by default)
  - Hover tooltips showing callsign, type, altitude, and ground speed
  - Click popup with full aircraft details (tail number, hex, squawk, fixes, time range)
  - Emergency aircraft highlighted in red with thicker lines
- **Emergency detection** — flags squawk codes 7500 (hijacking), 7600 (radio failure), and 7700 (general emergency)
- **SMS alerts** — optional Twilio integration in `alerts/aircraft_tracker.py`

---

## 🗂 Project Structure

```
Aircraft_Tracker/
├── collectors/
│   └── collect_my_api.py     # Main collection script (ADS-B Exchange)
├── analysis/
│   └── analysis_map.ipynb    # Jupyter notebook: data cleaning + Folium map
│   └── flight_map.html       # Rendered interactive map output
├── alerts/
│   └── aircraft_tracker.py   # Optional SMS alert script (Twilio)
├── data/
│   ├── YYYY-MM/              # Monthly folders (e.g. 2026-05/)
│   │   └── YYYY-MM-DD.csv    # One file per day
│   └── Archive/              # Legacy CSV files
├── logs/
│   └── error_log.txt
├── mapping.py                # ICAO type code → full name, military base coordinates
└── requirements.txt
```

---

## 🛠 Setup

### 1. Clone the repo

```bash
git clone https://github.com/jason-christopher/Aircraft_Tracker.git
cd Aircraft_Tracker
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Create a `.env` file

```env
MY_LAT=XX.XXXX
MY_LON=-XX.XXXX
ADSB_KEY=your_adsb_exchange_rapidapi_key

# Optional — only needed for SMS alerts
TWILIO_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_FROM=+1234567890
TWILIO_TO=+1987654321
```

---

## 🚀 Usage

### Collect data

```bash
python collectors/collect_my_api.py
```

Runs for up to 180 minutes (configurable via `MINUTES_TO_RUN`), polling every `MINUTES_BETWEEN_RUNS` minutes. Output is written to `data/YYYY-MM/YYYY-MM-DD.csv`. Safe to stop and restart — subsequent runs on the same day append to the existing file.

### Generate the map

Open `analysis/analysis_map.ipynb` in Jupyter and run all cells. The notebook auto-loads the most recent daily CSV and saves the rendered map to `analysis/flight_map.html`.

---

## ⚙️ Configuration

All tunable settings are near the top of `collectors/collect_my_api.py`:

| Setting | Default | Description |
|---|---|---|
| `DISTANCE_THRESHOLD_MILES` | `15000` | Max distance from your location to include an aircraft |
| `TYPES_TO_SEARCH` | See file | ICAO type codes to track (e.g. `C17`, `B52`, `E3TF`) |
| `MINUTES_TO_RUN` | `180` | How long each script run lasts |
| `MINUTES_BETWEEN_RUNS` | `1` | Polling interval in minutes |

---

## 🎨 Altitude Color Scale

| Color | Altitude |
|---|---|
| 🟠 Orange | 0 ft |
| 🟡 Yellow | 10,000 ft |
| 🟢 Green | 20,000 ft |
| 🩵 Cyan | 30,000 ft |
| 🔵 Blue | 35,000 ft |
| 🟣 Purple | 40,000 ft |
| 🔴 Red | 50,000 ft |
| ⬜ White | Altitude unknown |
| 🔴 Thick red | Emergency |

Colors interpolate linearly between stops.

---

## 🧪 Requirements

- Python 3.8+
- `requests`, `geopy`, `python-dotenv`
- `pandas`, `folium`, `numpy`
- `jupyter`, `ipykernel`
- `twilio` (optional, for SMS alerts)

See `requirements.txt` for pinned versions.

---

## 📜 License

MIT License — free to use, modify, and share.

---

## ✈️ Acknowledgments

- [ADS-B Exchange](https://adsbexchange.com) via [RapidAPI](https://rapidapi.com)
- [Folium](https://python-visualization.github.io/folium/)
- [Twilio](https://www.twilio.com)
