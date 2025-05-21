# Military Aircraft Tracker

This Python app monitors nearby military aircraft and sends you a text message if any are detected within a set radius (e.g., 30 miles) of your location.

It uses:
- [ADS-B Exchange API](https://rapidapi.com/adsbx/api/adsbexchange-com1) for live aircraft data
- [Twilio](https://www.twilio.com/) to send SMS alerts
- [geopy](https://geopy.readthedocs.io/) to calculate distances
- [dotenv](https://pypi.org/project/python-dotenv/) to manage configuration securely

---

## 📦 Features

- Filters military aircraft by type and proximity
- Maps ICAO type codes to human-readable aircraft names
- Includes heading direction (e.g., N, SW)
- Identifies squawk codes 7500/7600/7700 (hijack/lost comm/emergency)
- Sends alerts via SMS (optional)

---

## 🛠 Setup Instructions

### 1. Clone the Repo

```bash
git clone https://github.com/jason-christopher/Aircraft_Tracker.git
cd Aircraft_Tracker
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Create a `.env` File

Create a file named `.env` in the root directory and add:

```env
MY_LAT=XX.XXXX
MY_LON=-XX.XXXX
TWILIO_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_FROM=+1234567890
TWILIO_TO=+1987654321
ADSB_KEY=your_adsb_exchange_api_key
```

> Your latitude and longitude should be your home or monitoring location.

### 4. Run the Script

```bash
python aircraft_tracker.py 
```

---

## 📤 Alert Output Example

```
RCH123 (C-17A Globemaster) detected 12.3 miles away at 7,500 ft, heading SW.
```

---

## 📌 Notes

- To test without sending actual SMS, leave `send_sms()` commented.
- This script filters and formats aircraft types using a lookup dictionary (`TYPE_MAP`).
- Only aircraft with a known latitude/longitude and above ground level are considered.

---

## 🧪 Requirements

- Python 3.7+
- `requests`
- `geopy`
- `twilio`
- `python-dotenv`

---

## 📜 License

MIT License — free to use, modify, and share.

---

## ✈️ Acknowledgments

- [ADS-B Exchange](https://adsbexchange.com)
- [Twilio](https://www.twilio.com)
- [RapidAPI](https://rapidapi.com)
