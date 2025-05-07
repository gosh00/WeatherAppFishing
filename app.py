import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt

# ------------------- API KEYS -------------------
OPENWEATHER_API_KEY = 'your_openweather_api_key'  # Replace with your key

# ------------------- Helper Functions -------------------
def get_city_coordinates(city):
    try:
        url = f"http://api.openweathermap.org/geo/1.0/direct?q={city}&limit=1&appid={OPENWEATHER_API_KEY}"
        response = requests.get(url)
        response.raise_for_status()  # Raises an HTTPError if the response was an error
        data = response.json()
        if not data:
            return None
        return data[0].get('lat'), data[0].get('lon')
    except Exception as e:
        st.error(f"Failed to get coordinates for city '{city}'. Error: {e}")
        return None

def get_weather(lat, lon):
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric"
    response = requests.get(url)
    return response.json()

def get_nearby_water_bodies(lat, lon, radius=10000):
    overpass_url = "http://overpass-api.de/api/interpreter"
    query = f"""
    [out:json];
    (
      way(around:{radius},{lat},{lon})["natural"="water"];
      way(around:{radius},{lat},{lon})["waterway"];
    );
    out center;
    """
    response = requests.get(overpass_url, params={'data': query})
    return response.json()

def get_usgs_streamflow_data(lat, lon):
    usgs_url = f"https://waterservices.usgs.gov/nwis/iv/?format=json&bBox={lon-0.1},{lat-0.1},{lon+0.1},{lat+0.1}&parameterCd=00060&siteStatus=all"
    response = requests.get(usgs_url)
    data = response.json()
    return data['value']['timeSeries']

# ------------------- Streamlit UI -------------------
st.title("🎣 Weather & Fishing Spot Finder")

city = st.text_input("Enter a city:")

if city:
    coords = get_city_coordinates(city)
    if coords:
        lat, lon = coords
        st.map(pd.DataFrame([[lat, lon]], columns=["lat", "lon"]))

        # Show Weather
        st.subheader("🌤️ Current Weather")
        weather = get_weather(lat, lon)
        st.write(f"**{weather['weather'][0]['description'].capitalize()}**")
        st.write(f"Temperature: {weather['main']['temp']} °C")
        st.write(f"Wind Speed: {weather['wind']['speed']} m/s")
        st.write(f"Humidity: {weather['main']['humidity']}%")

        # Show Water Bodies
        st.subheader("💧 Nearby Lakes and Rivers")
        water_bodies = get_nearby_water_bodies(lat, lon)
        if water_bodies['elements']:
            df_water = pd.DataFrame([{
                'Name': el.get('tags', {}).get('name', 'Unnamed'),
                'Lat': el['center']['lat'],
                'Lon': el['center']['lon']
            } for el in water_bodies['elements']])
            st.map(df_water)
            st.dataframe(df_water)
        else:
            st.write("No nearby lakes or rivers found.")

        # USGS Streamflow Data
        st.subheader("📈 Water Current (USGS Streamflow)")
        try:
            streamflow_data = get_usgs_streamflow_data(lat, lon)
            for site in streamflow_data:
                site_name = site['sourceInfo']['siteName']
                values = site['values'][0]['value']
                times = [pd.to_datetime(v['dateTime']) for v in values]
                flows = [float(v['value']) for v in values]

                st.write(f"**{site_name}**")
                fig, ax = plt.subplots()
                ax.plot(times, flows, label='Flow (cfs)', color='blue')
                ax.set_ylabel("Cubic feet per second")
                ax.set_xlabel("Time")
                ax.legend()
                st.pyplot(fig)
        except Exception:
            st.write("No streamflow data available for this location.")
    else:
        st.error("City not found. Please try again.")
