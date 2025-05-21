
import os
import requests
from geopy.distance import geodesic
from twilio.rest import Client
import time
import re
from dotenv import load_dotenv

# --- LOAD .ENV ---

load_dotenv()

MY_LAT = float(os.getenv("MY_LAT"))
MY_LON = float(os.getenv("MY_LON"))

# --- SETTINGS ---

NON_MIL_CALLSIGN_PREFIXES = [
  # Commercial and cargo airline prefixes
  "AAL", "DAL", "UAL", "SKW", "ASA", "SWA", "JBU", "FFT", "NKS",
  "ENY", "ASH", "RPA", "PDT", "EDV", "AWI", "QXE",
  "FDX", "UPS", "GTI", "ABX",
  "BAW", "AFR", "KLM", "DLH", "ACA", "QFA", "JAL", "ANA", "UAE", "THY", "CXK",
]

# --- FUNCTIONS ---

def get_aircraft():
  url = "https://opensky-network.org/api/states/all?lamin=35.0000&lomin=-98.0000&lamax=36.0000&lomax=-97.0000"
  response = requests.get(url)
  if response.status_code == 200:
    return response.json().get('states', [])
  else:
    return []

def is_military(callsign):
  if not callsign:
    return False
  callsign = callsign.strip().upper()

  # Match known commercial/cargo airline prefixes
  for prefix in NON_MIL_CALLSIGN_PREFIXES:
    if callsign.startswith(prefix):
      return False
  # Match FAA-style general aviation N-numbers
  if re.fullmatch(r"N\d{1,5}[A-Z]{0,2}", callsign):
    return False
  return True

def send_sms(message):
    client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
    client.messages.create(body=message, from_=TWILIO_FROM, to=TWILIO_TO)

def check_nearby_aircraft():
  aircraft_list = get_aircraft()
  for plane in aircraft_list:
    try:
      callsign = plane[1].strip()
      origin_country = plane[2]
      lat = plane[6]
      lon = plane[5]
      if lat is None or lon is None:
        continue
      if is_military(callsign):
        distance = geodesic((MY_LAT, MY_LON), (lat, lon)).miles
        if distance <= 90:
          msg = f"Military aircraft '{callsign}' detected {distance:.2f} miles away."
          print(msg)
          # send_sms(msg)
          return  # Send only one alert per cycle
    except Exception as e:
      print(f"Error processing aircraft: {e}")

# --- MAIN LOOP ---

if __name__ == "__main__":
  check_nearby_aircraft()
