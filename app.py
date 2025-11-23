import streamlit as st
from urllib.request import Request, urlopen
from urllib.parse import urlencode
import json

st.set_page_config(page_title="Tourism & Weather Agent")

# --------------------- HTTP Client ---------------------
class HttpClient:
    def get_json(self, url, params=None, headers=None):
        q = "" if not params else ("?" + urlencode(params))
        h = {"User-Agent": "Inkle-TourismAgent/1.0"}
        if headers:
            h.update(headers)
        req = Request(url + q, headers=h)
        try:
            with urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception:
            return None

    def post_json(self, url, body, headers=None):
        h = {"User-Agent": "Inkle-TourismAgent/1.0", "Accept": "application/json"}
        if headers:
            h.update(headers)
        req = Request(url, data=body.encode("utf-8"), headers=h)
        try:
            with urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception:
            return None

# --------------------- Geocoder ---------------------
class Geocoder:
    def __init__(self, http):
        self.http = http

    def geocode(self, query):
        params = {"q": query, "format": "json", "limit": 1, "addressdetails": 0}
        headers = {"Referer": "https://inkle.local"}
        data = self.http.get_json("https://nominatim.openstreetmap.org/search", params, headers)
        if not data:
            return None
        item = data[0]
        try:
            lat = float(item["lat"])
            lon = float(item["lon"])
        except:
            return None
        return {"name": item.get("display_name", query).split(",")[0], "lat": lat, "lon": lon}

# --------------------- Weather Agent ---------------------
class WeatherAgent:
    def __init__(self, http):
        self.http = http

    def weather(self, lat, lon):
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,precipitation",
            "hourly": "precipitation_probability",
            "timezone": "auto",
        }
        data = self.http.get_json("https://api.open-meteo.com/v1/forecast", params)
        if not data:
            return {"temperature_c": None, "precip_chance": 0}
        current = data.get("current", {})
        hourly = data.get("hourly", {})
        temps = current.get("temperature_2m")
        probs = hourly.get("precipitation_probability") or []
        return {"temperature_c": temps, "precip_chance": int(probs[0]) if probs else 0}

# --------------------- Places Agent ---------------------
class PlacesAgent:
    def __init__(self, http):
        self.http = http

    def places(self, lat, lon, limit=5):
        q = f"""
        [out:json][timeout:25];
        ( node["tourism"](around:15000,{lat},{lon});
          way["tourism"](around:15000,{lat},{lon});
          relation["tourism"](around:15000,{lat},{lon});
        );
        out tags;
        """
        data = self.http.post_json("https://overpass-api.de/api/interpreter", q.strip(), {"Content-Type": "text/plain"})
        if not data:
            return []
        names = []
        seen = set()
        for el in data.get("elements", []):
            n = (el.get("tags") or {}).get("name")
            if n and n not in seen:
                seen.add(n)
                names.append(n)
                if len(names) >= limit:
                    break
        return names

# --------------------- Tourism Agent ---------------------
class TourismAgent:
    def __init__(self):
        self.http = HttpClient()
        self.geocoder = Geocoder(self.http)
        self.weather_agent = WeatherAgent(self.http)
        self.places_agent = PlacesAgent(self.http)

    def respond(self, place):
        loc = self.geocoder.geocode(place)
        if not loc:
            return "❌ Unknown place."

        name, lat, lon = loc["name"], loc["lat"], loc["lon"]
        w = self.weather_agent.weather(lat, lon)
        p = self.places_agent.places(lat, lon)

        result = f"🌍 **{name}**\n"
        if w.get("temperature_c") is not None:
            result += f"🌡 Temperature: **{round(w['temperature_c'])}°C**\n"
            result += f"🌧 Chance of rain: **{w['precip_chance']}%**\n"
        if p:
            result += "\n🧭 **Places to visit:**\n"
            for x in p:
                result += f"• {x}\n"
        return result

# --------------------- Streamlit UI ---------------------
st.title("🌎 Tourism & Weather Recommendation Agent")
place = st.text_input("Enter a place (example: Paris, Goa, London)")

if st.button("Search"):
    agent = TourismAgent()
    with st.spinner("Getting info..."):
        reply = agent.respond(place)
    st.markdown(reply)
