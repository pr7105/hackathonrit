import pandas as pd
import folium
from folium.plugins import HeatMap, MarkerCluster, TimestampedGeoJson
import streamlit as st
from streamlit_folium import st_folium
import os
import http.client
import json

# Set up the Streamlit app layout
st.set_page_config(layout="wide")
st.markdown("""
    <style>
        .main .block-container {
            padding-top: 0rem;
            padding-bottom: 0rem;
            padding-left: 0rem;
            padding-right: 0rem;
        }
        .map-container {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            width: 100%;
        }
        .map-content {
            flex: 1;
            min-width: 0;
            margin-right: 10px;
        }
    </style>
    """, unsafe_allow_html=True)

# Function to send SMS via Infobip API
def send_sms():
    conn = http.client.HTTPSConnection("g9g3yw.api.infobip.com")
    payload = json.dumps({
        "messages": [
            {
                "destinations": [{"to": "385981921597"}],
                "from": "447491163443",
                "text": "Pollution is too high, we suggest you move to a different area"
            }
        ]
    })
    headers = {
        'Authorization': 'App 95cd05a638ad50936b440bffaa803d7e-25933a58-d3a0-4d97-9f8b-410aa17db982',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    conn.request("POST", "/sms/2/text/advanced", payload, headers)
    res = conn.getresponse()
    data = res.read()
    return data.decode("utf-8")  # Return response data for confirmation

# Function to load CSV data
@st.cache_data
def load_data(glider_file, drone_file):
    glider_df = pd.read_csv(glider_file)
    glider_df.columns = ['Unnamed: 0', 'time', 'P2_5', 'unknown', 'P10', 'UV', 'CO', 'Fire', 'H2', 'Temp', 'Hum', 'Lat', 'Long', 'Alt']
    glider_df['time'] = pd.to_datetime(glider_df['time'], errors='coerce')

    drone_df = pd.read_csv(drone_file, delimiter=';')
    drone_df.columns = ['Unnamed: 0', 'Timestamp', 'Millis', 'Particles>0.3um', 'Particles>0.5um', 
                        'Particles>1.0um', 'Particles>2.5um', 'Particles>5.0um', 
                        'Particles>10.0um', 'PM1.0', 'PM2.5', 'PM10', 'Humidity', 
                        'Temperature', 'flight_iteration', 'Lat', 'Long', 'Alt']
    drone_df['Timestamp'] = pd.to_datetime(drone_df['Timestamp'], errors='coerce')
    
    return glider_df, drone_df

# Enhanced CO Visualization: Bigger, modern-looking orange circles with centered values
def create_co_columns(m, data):
    if not data.empty and 'CO' in data.columns and 'Alt' in data.columns:
        for _, row in data.iterrows():
            co_level = row['CO']
            altitude = row['Alt']
            if pd.notnull(co_level) and pd.notnull(altitude):
                radius = max(co_level * 3, 15)  # Increased radius for better visibility
                
                # Adding a modern-looking CircleMarker with a smooth orange gradient
                folium.CircleMarker(
                    location=[row['Lat'], row['Long']],
                    radius=radius,
                    color='rgba(255, 165, 0, 0.9)',  # Orange color
                    weight=2,
                    fill=True,
                    fill_color='rgba(255, 140, 0, 0.7)',  # Slight gradient for modern look
                    fill_opacity=0.85,
                    popup=f"CO Level: {co_level} ppm",
                    tooltip=f"Altitude: {altitude} m"
                ).add_to(m)

                # Adding a soft shadow effect for better visibility and 3D look
                folium.CircleMarker(
                    location=[row['Lat'], row['Long']],
                    radius=radius + 6,  # Shadow slightly larger than the circle
                    color='rgba(0, 0, 0, 0.2)',  # Shadow effect
                    weight=1,
                    fill=True,
                    fill_opacity=0.3
                ).add_to(m)

                # Center the numerical CO value with smaller font size
                folium.Marker(
                    location=[row['Lat'], row['Long']],
                    icon=folium.DivIcon(html=f"""
                        <div style="font-size: 8pt; font-weight: bold; color: black; 
                                    display: flex; align-items: center; justify-content: center;
                                    width: {radius*2}px; height: {radius*2}px; border-radius: 50%; 
                                    background-color: rgba(255, 140, 0, 0);">
                            {co_level:.2f}
                        </div>
                    """)
                ).add_to(m)
    else:
        st.sidebar.warning("No valid CO data available for visualization.")

# Function to create heatmaps
def add_heatmap(m, data, value_column, gradient):
    if not data.empty:
        heat_data = [[row['Lat'], row['Long'], row[value_column]] for _, row in data.iterrows() if not pd.isnull(row[value_column])]
        if heat_data:
            HeatMap(data=heat_data, radius=20, blur=15, max_zoom=1, gradient=gradient).add_to(m)

# Function to create Folium map with markers
def create_map(initial_location, zoom):
    m = folium.Map(location=initial_location, zoom_start=zoom, tiles="OpenStreetMap")
    return m

# Function to add markers for glider and drone data with all CSV data in popup
def add_markers(m, glider_df, drone_df, co_selected, show_markers):
    if show_markers and not co_selected:  # Only add markers if "Show Markers" is enabled and CO visualization is not selected
        if not glider_df.empty:
            for _, row in glider_df.iterrows():
                popup_content = f"""
                <strong>Glider Data:</strong><br>
                <ul>
                    <li><strong>Time:</strong> {row['time']}</li>
                    <li><strong>PM2.5:</strong> {row['P2_5']} µg/m³</li>
                    <li><strong>PM10:</strong> {row['P10']} µg/m³</li>
                    <li><strong>Unknown:</strong> {row['unknown']}</li>
                    <li><strong>UV:</strong> {row['UV']} µW/cm²</li>
                    <li><strong>CO:</strong> {row['CO']} ppm</li>
                    <li><strong>Fire:</strong> {row['Fire']}</li>
                    <li><strong>H2:</strong> {row['H2']}</li>
                    <li><strong>Temperature:</strong> {row['Temp']} °C</li>
                    <li><strong>Humidity:</strong> {row['Hum']}%</li>
                    <li><strong>Latitude:</strong> {row['Lat']}</li>
                    <li><strong>Longitude:</strong> {row['Long']}</li>
                    <li><strong>Altitude:</strong> {row['Alt']} m</li>
                </ul>
                """
                folium.Marker(
                    location=[row['Lat'], row['Long']],
                    icon=folium.Icon(color='orange', icon='plane', prefix='fa', icon_color='black'),
                    popup=popup_content
                ).add_to(m)

        if not drone_df.empty:
            for _, row in drone_df.iterrows():
                popup_content = f"""
                <strong>Drone Data:</strong><br>
                <ul>
                    <li><strong>Timestamp:</strong> {row['Timestamp']}</li>
                    <li><strong>Millis:</strong> {row['Millis']}</li>
                    <li><strong>Particles &gt;0.3µm:</strong> {row['Particles>0.3um']}</li>
                    <li><strong>Particles &gt;0.5µm:</strong> {row['Particles>0.5um']}</li>
                    <li><strong>Particles &gt;1.0µm:</strong> {row['Particles>1.0um']}</li>
                    <li><strong>Particles &gt;2.5µm:</strong> {row['Particles>2.5um']}</li>
                    <li><strong>Particles &gt;5.0µm:</strong> {row['Particles>5.0um']}</li>
                    <li><strong>Particles &gt;10.0µm:</strong> {row['Particles>10.0um']}</li>
                    <li><strong>PM1.0:</strong> {row['PM1.0']} µg/m³</li>
                    <li><strong>PM2.5:</strong> {row['PM2.5']} µg/m³</li>
                    <li><strong>PM10:</strong> {row['PM10']} µg/m³</li>
                    <li><strong>Humidity:</strong> {row['Humidity']}%</li>
                    <li><strong>Temperature:</strong> {row['Temperature']} °C</li>
                    <li><strong>Flight Iteration:</strong> {row['flight_iteration']}</li>
                    <li><strong>Latitude:</strong> {row['Lat']}</li>
                    <li><strong>Longitude:</strong> {row['Long']}</li>
                    <li><strong>Altitude:</strong> {row['Alt']} m</li>
                </ul>
                """
                folium.Marker(
                    location=[row['Lat'], row['Long']],
                    icon=folium.Icon(color='orange', icon='rocket', prefix='fa', icon_color='black'),
                    popup=popup_content
                ).add_to(m)

# Function to add flight path visualization
def create_flight_path(m, data, color='blue'):
    if not data.empty:
        coordinates = data[['Lat', 'Long']].dropna().values.tolist()
        if len(coordinates) > 1:  # Ensure there are enough points to create a path
            folium.PolyLine(locations=coordinates, color=color, weight=3).add_to(m)

# Function to add marker clustering visualization
def create_marker_cluster(m, data):
    if not data.empty:
        marker_cluster = MarkerCluster().add_to(m)
        for _, row in data.iterrows():
            if not pd.isnull(row['Lat']) and not pd.isnull(row['Long']):
                folium.Marker(
                    location=[row['Lat'], row['Long']],
                    popup=f"Data Point: {row['Lat']}, {row['Long']}"
                ).add_to(marker_cluster)

# Function to add altitude heatmap
def create_altitude_heatmap(m, data):
    if not data.empty and 'Alt' in data.columns:
        altitude_data = [[row['Lat'], row['Long'], row['Alt']] for _, row in data.iterrows() if not pd.isnull(row['Alt'])]
        if altitude_data:
            HeatMap(data=altitude_data, radius=20, blur=15, max_zoom=1, gradient={0.0: 'blue', 0.5: 'yellow', 1.0: 'red'}).add_to(m)

# Function to add time-based flight path animation
def create_time_based_path(m, data):
    if not data.empty and 'time' in data.columns:
        features = []
        for _, row in data.iterrows():
            if not pd.isnull(row['Lat']) and not pd.isnull(row['Long']):
                features.append({
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Point',
                        'coordinates': [row['Long'], row['Lat']],
                    },
                    'properties': {
                        'time': row['time'].strftime("%Y-%m-%dT%H:%M:%SZ") if pd.notnull(row['time']) else None,
                        'popup': f"Time: {row['time']}",
                        'icon': 'circle',
                        'iconstyle': {'fillColor': 'red', 'fillOpacity': 0.6, 'stroke': 'true', 'radius': 8}
                    }
                })
        geojson = {
            'type': 'FeatureCollection',
            'features': features
        }
        TimestampedGeoJson(geojson, period='PT1M', add_last_point=True, auto_play=False, loop=False).add_to(m)

def main():
    # Get the directory of the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Specify file paths relative to the script's directory
    glider_file = os.path.join(script_dir, 'glider.csv')
    drone_file = os.path.join(script_dir, 'drone.csv')

    # Load data
    glider_data, drone_data = load_data(glider_file, drone_file)

    # Set default map location and zoom
    initial_location = [45.7159259336489, 16.345156414198076]  # Ivanic Grad coordinates
    default_zoom = 16

    # Restore previous map state if available
    if 'map_location' not in st.session_state:
        st.session_state.map_location = initial_location
    if 'map_zoom' not in st.session_state:
        st.session_state.map_zoom = default_zoom

    # Sidebar for heatmap options
    st.sidebar.subheader("Heatmap Options")
    humidity = st.sidebar.checkbox("Humidity Heatmap", key="humidity_checkbox")
    temp = st.sidebar.checkbox("Temperature Heatmap", key="temp_checkbox")
    pm25 = st.sidebar.checkbox("PM2.5 Heatmap", key="pm25_checkbox")
    pm10 = st.sidebar.checkbox("PM10 Heatmap", key="pm10_checkbox")
    pm5 = st.sidebar.checkbox("PM5 Heatmap", key="pm5_checkbox")
    co = st.sidebar.checkbox("CO Visualization", key="co_checkbox")

    # Toggle for showing or hiding map markers (default: True)
    show_markers = st.sidebar.checkbox("Show Map Markers", value=True, key="show_markers_checkbox")

    # Checkbox for flight path visualization
    show_flight_path = st.sidebar.checkbox("Show Flight Paths", key="flight_path_checkbox")

    # New checkboxes for cool features
    show_marker_cluster = st.sidebar.checkbox("Show Glider Marker Clustering", key="marker_cluster_checkbox")
    show_altitude_heatmap = st.sidebar.checkbox("Show Glider Altitude Heatmap", key="altitude_heatmap_checkbox")
    show_time_based_path = st.sidebar.checkbox("Show Glider Path", key="time_based_path_checkbox")

    # Button to send SMS in the sidebar
    if st.sidebar.button("Pollution too high"):
        response = send_sms()
        st.sidebar.success(f"SMS sent successfully! Response: {response}")

    # Create the map
    m = create_map(st.session_state.map_location, st.session_state.map_zoom)
    
    # Add markers for the data, but skip if CO visualization is active or markers are toggled off
    add_markers(m, glider_data, drone_data, co, show_markers)

    # Add heatmaps based on user selections
    if humidity:
        combined_humidity_data = pd.concat([glider_data[['Lat', 'Long', 'Hum']].rename(columns={'Hum': 'Humidity'}), 
                                             drone_data[['Lat', 'Long', 'Humidity']]]).dropna()
        add_heatmap(m, combined_humidity_data, 'Humidity', {0.0: 'blue', 0.5: 'lime', 1.0: 'red'})

    if temp:
        combined_temp_data = pd.concat([glider_data[['Lat', 'Long', 'Temp']].rename(columns={'Temp': 'Temperature'}), 
                                          drone_data[['Lat', 'Long', 'Temperature']]]).dropna()
        add_heatmap(m, combined_temp_data, 'Temperature', {0.0: 'blue', 0.5: 'yellow', 1.0: 'red'})

    if pm25:
        combined_pm25_data = pd.concat([glider_data[['Lat', 'Long', 'P2_5']].rename(columns={'P2_5': 'PM2.5'}), 
                                         drone_data[['Lat', 'Long', 'PM2.5']]]).dropna()
        add_heatmap(m, combined_pm25_data, 'PM2.5', {0.0: 'blue', 0.5: 'yellow', 1.0: 'red'})

    if pm10:
        combined_pm10_data = pd.concat([glider_data[['Lat', 'Long', 'P10']].rename(columns={'P10': 'PM10'}), 
                                         drone_data[['Lat', 'Long', 'PM10']]]).dropna()
        add_heatmap(m, combined_pm10_data, 'PM10', {0.0: 'blue', 0.5: 'yellow', 1.0: 'red'})

    if pm5:
        pm5_data = glider_data[['Lat', 'Long', 'unknown']].rename(columns={'unknown': 'PM5'}).dropna()
        add_heatmap(m, pm5_data, 'PM5', {0.0: 'blue', 0.5: 'yellow', 1.0: 'red'})

    # If CO checkbox is selected, show the CO columns with enhanced modern orange circles
    if co:
        create_co_columns(m, glider_data)

    # If flight path checkbox is selected, show the flight path
    if show_flight_path:
        create_flight_path(m, glider_data, color='green')  # Glider path in green
        create_flight_path(m, drone_data, color='red')  # Drone path in red

    # New cool features
    if show_marker_cluster:
        create_marker_cluster(m, glider_data)

    if show_altitude_heatmap:
        create_altitude_heatmap(m, glider_data)

    if show_time_based_path:
        create_time_based_path(m, glider_data)

    # Display the map and capture any new interactions
    st_folium(m, width=2000, height=800, key="map_display")

if __name__ == "__main__":
    main()