import pandas as pd
import folium
from folium.plugins import HeatMap
import streamlit as st
from streamlit_folium import st_folium

# Configure the page layout to be wide
st.set_page_config(layout="wide")

# Function to load CSV data
@st.cache_data
def load_data(glider_file, drone_file):
    # Load glider data
    glider_df = pd.read_csv(glider_file)
    glider_df.columns = ['Unnamed: 0', 'time', 'P2_5', 'unknown', 'P10', 'UV', 'CO', 'Fire', 'H2', 'Temp', 'Hum', 'Lat', 'Long', 'Alt']
    
    # Convert 'time' column to datetime
    glider_df['time'] = pd.to_datetime(glider_df['time'], errors='coerce')
    
    # Load drone data
    drone_df = pd.read_csv(drone_file, delimiter=';')
    drone_df.columns = ['Unnamed: 0', 'Timestamp', 'Millis', 'Particles>0.3um', 'Particles>0.5um', 
                        'Particles>1.0um', 'Particles>2.5um', 'Particles>5.0um', 
                        'Particles>10.0um', 'PM1.0', 'PM2.5', 'PM10', 'Humidity', 
                        'Temperature', 'flight_iteration', 'Lat', 'Long', 'Alt']
    
    # Convert 'Timestamp' to datetime
    drone_df['Timestamp'] = pd.to_datetime(drone_df['Timestamp'], errors='coerce')
    
    return glider_df, drone_df

# Function to create heatmaps
def add_heatmap(m, data, value_column, gradient):
    if not data.empty:
        heat_data = [[row['Lat'], row['Long'], row[value_column]] for _, row in data.iterrows()]
        HeatMap(data=heat_data, radius=25, blur=15, max_zoom=1, gradient=gradient).add_to(m)

# Function to generate the legend text to display
def generate_legend_html(title, color_scale):
    legend_html = f"""
    <div style="
    background-color: white; border:2px solid grey; padding: 10px; font-size:14px;">
    <h4>{title}</h4>
    <i style="background: blue; width: 20px; height: 20px; display: inline-block;"></i> Low<br>
    <i style="background: {color_scale[0.5]}; width: 20px; height: 20px; display: inline-block;"></i> Moderate<br>
    <i style="background: {color_scale[1.0]}; width: 20px; height: 20px; display: inline-block;"></i> High<br>
    </div>
    """
    return legend_html

# Function to create Folium map
@st.cache_data
def create_map(glider_df, drone_df, selected_iterations, heatmap_opts):
    ivanic_grad_coords = [45.719999, 16.3418]
    m = folium.Map(location=ivanic_grad_coords, zoom_start=16)

    # Add glider markers
    if not glider_df.empty:
        for _, row in glider_df.iterrows():
            popup_content = "<strong>Glider Data:</strong><br>" + "<br>".join([f"{col}: {row[col]}" for col in row.index])
            folium.Marker(
                location=[row['Lat'], row['Long']],
                icon=folium.Icon(color='orange', icon='plane', prefix='fa', icon_color='black'),
                popup=popup_content
            ).add_to(m)

    # Add drone markers
    if not drone_df.empty:
        drone_df_filtered = drone_df[drone_df['flight_iteration'].isin(selected_iterations)]
        for _, row in drone_df_filtered.iterrows():
            popup_content = "<strong>Drone Data:</strong><br>" + "<br>".join([f"{col}: {row[col]}" for col in row.index])
            folium.Marker(
                location=[row['Lat'], row['Long']],
                icon=folium.Icon(color='orange', icon='rocket', prefix='fa', icon_color='black'),
                popup=popup_content
            ).add_to(m)

    # Heatmaps and legends
    legends = ""
    if heatmap_opts['humidity']:
        combined_humidity_data = pd.concat([glider_df[['Lat', 'Long', 'Hum']].rename(columns={'Hum': 'Humidity'}), drone_df[['Lat', 'Long', 'Humidity']]]).dropna()
        add_heatmap(m, combined_humidity_data, 'Humidity', {0.0: 'blue', 0.5: 'lime', 1.0: 'red'})
        legends += generate_legend_html("Humidity", {0.5: 'lime', 1.0: 'red'})

    if heatmap_opts['temp']:
        combined_temp_data = pd.concat([glider_df[['Lat', 'Long', 'Temp']].rename(columns={'Temp': 'Temperature'}), drone_df[['Lat', 'Long', 'Temperature']]]).dropna()
        add_heatmap(m, combined_temp_data, 'Temperature', {0.0: 'blue', 0.5: 'yellow', 1.0: 'red'})
        legends += generate_legend_html("Temperature", {0.5: 'yellow', 1.0: 'red'})

    if heatmap_opts['pm25']:
        combined_pm25_data = pd.concat([glider_df[['Lat', 'Long', 'P2_5']].rename(columns={'P2_5': 'PM2.5'}), drone_df[['Lat', 'Long', 'PM2.5']]]).dropna()
        add_heatmap(m, combined_pm25_data, 'PM2.5', {0.0: 'blue', 0.5: 'yellow', 1.0: 'red'})
        legends += generate_legend_html("PM2.5", {0.5: 'yellow', 1.0: 'red'})

    if heatmap_opts['pm10']:
        combined_pm10_data = pd.concat([glider_df[['Lat', 'Long', 'P10']].rename(columns={'P10': 'PM10'}), drone_df[['Lat', 'Long', 'PM10']]]).dropna()
        add_heatmap(m, combined_pm10_data, 'PM10', {0.0: 'blue', 0.5: 'yellow', 1.0: 'red'})
        legends += generate_legend_html("PM10", {0.5: 'yellow', 1.0: 'red'})

    return m, legends

# Main function for Streamlit app
def main():
    glider_file = '/Users/petra/Desktop/glider.csv'
    drone_file = '/Users/petra/Desktop/drone.csv'

    # Load data
    glider_data, drone_data = load_data(glider_file, drone_file)

    st.sidebar.subheader("Show Markers")
    show_all_gliders = st.sidebar.checkbox("Show All Glider Markers", value=True)
    show_all_drones = st.sidebar.checkbox("Show All Drone Markers", value=True)

    glider_data_to_use = pd.DataFrame()
    drone_data_to_use = pd.DataFrame()
    selected_iterations = []

    if show_all_gliders:
        st.sidebar.subheader("Select Time Range for Glider Data")
        min_time, max_time = glider_data['time'].min(), glider_data['time'].max()

        if pd.isnull(min_time) or pd.isnull(max_time):
            st.error("Glider time data is missing or invalid.")
            return

        selected_time_range = st.sidebar.slider(
            "Select time range for Glider",
            min_value=min_time.to_pydatetime(),  
            max_value=max_time.to_pydatetime(),
            value=(min_time.to_pydatetime(), max_time.to_pydatetime()),
            format="YYYY-MM-DD HH:mm"
        )

        glider_data_to_use = glider_data[(glider_data['time'] >= selected_time_range[0]) & 
                                         (glider_data['time'] <= selected_time_range[1])]

    if show_all_drones:
        st.sidebar.subheader("Select Time Range for Drone Data")
        min_drone_time, max_drone_time = drone_data['Timestamp'].min(), drone_data['Timestamp'].max()

        if pd.isnull(min_drone_time) or pd.isnull(max_drone_time):
            st.error("Drone time data is missing or invalid.")
            return

        selected_drone_time_range = st.sidebar.slider(
            "Select time range for Drone",
            min_value=min_drone_time.to_pydatetime(),  
            max_value=max_drone_time.to_pydatetime(),
            value=(min_drone_time.to_pydatetime(), max_drone_time.to_pydatetime()),
            format="YYYY-MM-DD HH:mm"
        )

        drone_data_to_use = drone_data[(drone_data['Timestamp'] >= selected_drone_time_range[0]) & 
                                       (drone_data['Timestamp'] <= selected_drone_time_range[1])]

        # Select flight iterations
        selected_iterations = st.sidebar.multiselect(
            "Select flight iterations for Drone",
            options=drone_data_to_use['flight_iteration'].unique().tolist(),
            default=drone_data_to_use['flight_iteration'].unique().tolist()
        )

    st.sidebar.subheader("Heatmaps Options")
    heatmap_opts = {
        'humidity': st.sidebar.checkbox("Humidity Heatmap", value=False),
        'temp': st.sidebar.checkbox("Temperature Heatmap", value=False),
        'pm25': st.sidebar.checkbox("PM2.5 Heatmap", value=False),
        'pm10': st.sidebar.checkbox("PM10 Heatmap", value=False)
    }

    # Create map
    map_object, legends_html = create_map(glider_data_to_use, drone_data_to_use, selected_iterations, heatmap_opts)

    st_folium(map_object, width=800, height=600)

    if legends_html:
        st.components.v1.html(legends_html, height=200)

if __name__ == "__main__":
    main()


# import pandas as pd
# import folium
# from folium.plugins import HeatMap
# import streamlit as st
# from streamlit_folium import st_folium

# # Configure the page layout to be wide
# st.set_page_config(layout="wide")

# # Function to load CSV data
# @st.cache_data
# def load_data(glider_file, drone_file):
#     # Load and clean glider and drone data
#     glider_df = pd.read_csv(glider_file)
#     drone_df = pd.read_csv(drone_file, delimiter=';')
    
#     glider_df.columns = ['Unnamed: 0', 'time', 'P2_5', 'unknown', 'P10', 'UV', 'CO', 'Fire', 'H2', 'Temp', 'Hum', 'Lat', 'Long', 'Alt']
#     drone_df.columns = ['Unnamed: 0', 'Timestamp', 'Millis', 'Particles>0.3um', 'Particles>0.5um', 'Particles>1.0um', 
#                         'Particles>2.5um', 'Particles>5.0um', 'Particles>10.0um', 'PM1.0', 'PM2.5', 'PM10', 'Humidity', 
#                         'Temperature', 'flight_iteration', 'Lat', 'Long', 'Alt']

#     glider_df['time'] = pd.to_datetime(glider_df['time'], errors='coerce')
#     drone_df['Timestamp'] = pd.to_datetime(drone_df['Timestamp'], errors='coerce')

#     return glider_df, drone_df

# # Function to create heatmaps
# def add_heatmap(m, data, value_column, gradient):
#     if not data.empty:
#         heat_data = [[row['Lat'], row['Long'], row[value_column]] for _, row in data.iterrows()]
#         HeatMap(data=heat_data, radius=25, blur=15, max_zoom=1, gradient=gradient).add_to(m)

# # Function to generate the legend text to display
# def generate_legend_html(title, color_scale):
#     legend_html = f"""
#     <div style="
#     background-color: white; border:2px solid grey; padding: 10px; font-size:14px;">
#     <h4>{title}</h4>
#     <i style="background: blue; width: 20px; height: 20px; display: inline-block;"></i> Low<br>
#     <i style="background: {color_scale[0.5]}; width: 20px; height: 20px; display: inline-block;"></i> Moderate<br>
#     <i style="background: {color_scale[1.0]}; width: 20px; height: 20px; display: inline-block;"></i> High<br>
#     </div>
#     """
#     return legend_html

# # Function to create Folium map
# @st.cache_data
# def create_map(glider_df, drone_df, selected_iterations, heatmap_opts):
#     ivanic_grad_coords = [45.719999, 16.3418]
#     m = folium.Map(location=ivanic_grad_coords, zoom_start=16)

#     # Filter drone data by flight iterations
#     drone_df_filtered = drone_df[drone_df['flight_iteration'].isin(selected_iterations)] if selected_iterations else drone_df

#     # Markers
#     for df, icon, label in [(glider_df, 'plane', 'Glider Data'), (drone_df_filtered, 'rocket', 'Drone Data')]:
#         for _, row in df.iterrows():
#             popup_content = f"<strong>{label}:</strong><br>" + "<br>".join([f"{col}: {row[col]}" for col in row.index])
#             folium.Marker([row['Lat'], row['Long']], icon=folium.Icon(color='orange', icon=icon, prefix='fa'), popup=popup_content).add_to(m)

#     # Heatmaps and legends
#     legends = ""
#     if heatmap_opts['humidity']:
#         combined_humidity_data = pd.concat([glider_df[['Lat', 'Long', 'Hum']].rename(columns={'Hum': 'Humidity'}), drone_df[['Lat', 'Long', 'Humidity']]]).dropna()
#         add_heatmap(m, combined_humidity_data, 'Humidity', {0.0: 'blue', 0.5: 'lime', 1.0: 'red'})
#         legends += generate_legend_html("Humidity", {0.5: 'lime', 1.0: 'red'})

#     if heatmap_opts['temp']:
#         combined_temp_data = pd.concat([glider_df[['Lat', 'Long', 'Temp']].rename(columns={'Temp': 'Temperature'}), drone_df[['Lat', 'Long', 'Temperature']]]).dropna()
#         add_heatmap(m, combined_temp_data, 'Temperature', {0.0: 'blue', 0.5: 'yellow', 1.0: 'red'})
#         legends += generate_legend_html("Temperature", {0.5: 'yellow', 1.0: 'red'})

#     if heatmap_opts['pm25']:
#         combined_pm25_data = pd.concat([glider_df[['Lat', 'Long', 'P2_5']].rename(columns={'P2_5': 'PM2.5'}), drone_df[['Lat', 'Long', 'PM2.5']]]).dropna()
#         add_heatmap(m, combined_pm25_data, 'PM2.5', {0.0: 'blue', 0.5: 'yellow', 1.0: 'red'})
#         legends += generate_legend_html("PM2.5", {0.5: 'yellow', 1.0: 'red'})

#     if heatmap_opts['pm10']:
#         combined_pm10_data = pd.concat([glider_df[['Lat', 'Long', 'P10']].rename(columns={'P10': 'PM10'}), drone_df[['Lat', 'Long', 'PM10']]]).dropna()
#         add_heatmap(m, combined_pm10_data, 'PM10', {0.0: 'blue', 0.5: 'yellow', 1.0: 'red'})
#         legends += generate_legend_html("PM10", {0.5: 'yellow', 1.0: 'red'})

#     return m, legends

# # Main function for Streamlit app
# def main():
#     glider_file, drone_file = '/Users/petra/Desktop/glider.csv', '/Users/petra/Desktop/drone.csv'
#     glider_data, drone_data = load_data(glider_file, drone_file)

#     # Sidebar
#     st.sidebar.subheader("Show Markers")
#     show_all_gliders = st.sidebar.checkbox("Show Glider Markers", value=True)
#     show_all_drones = st.sidebar.checkbox("Show Drone Markers", value=True)

#     # Glider Time Filter
#     glider_data_to_use, drone_data_to_use = pd.DataFrame(), pd.DataFrame()
#     if show_all_gliders:
#         min_time = glider_data['time'].min().to_pydatetime()  # Convert Timestamp to datetime
#         max_time = glider_data['time'].max().to_pydatetime()  # Convert Timestamp to datetime

#         # Now use the converted time range in the slider
#         time_range = st.sidebar.slider("Glider Time Range", value=(min_time, max_time))
#         glider_data_to_use = glider_data[(glider_data['time'] >= time_range[0]) & (glider_data['time'] <= time_range[1])]

#     # Drone Time & Iteration Filters
#     if show_all_drones:
#         min_drone_time = drone_data['Timestamp'].min().to_pydatetime()  # Convert Timestamp to datetime
#         max_drone_time = drone_data['Timestamp'].max().to_pydatetime()  # Convert Timestamp to datetime

#         drone_time_range = st.sidebar.slider("Drone Time Range", value=(min_drone_time, max_drone_time))
#         drone_data_filtered = drone_data[(drone_data['Timestamp'] >= drone_time_range[0]) & (drone_data['Timestamp'] <= drone_time_range[1])]
#         selected_iterations = st.sidebar.multiselect("Flight Iterations", options=drone_data['flight_iteration'].unique(), default=drone_data['flight_iteration'].unique())
#         drone_data_to_use = drone_data_filtered

#     # Heatmap options
#     st.sidebar.subheader("Heatmap Options")
#     heatmap_opts = {opt: st.sidebar.checkbox(f"Show {opt.capitalize()} Heatmap", value=False) for opt in ['humidity', 'temp', 'pm25', 'pm10']}

#     # Create layout with map and legends side by side
#     col1, col2 = st.columns([3, 1])

#     with col1:
#         # Create and display map
#         if not glider_data_to_use.empty or not drone_data_to_use.empty:
#             map_, legends = create_map(glider_data_to_use, drone_data_to_use, selected_iterations, heatmap_opts)
#             st_folium(map_, width=700, height=500)
#         else:
#             st.warning("No data available for the selected filters.")
    
#     with col2:
#         # Display legends in the second column
#         st.markdown(legends, unsafe_allow_html=True)

# if __name__ == "__main__":
#     main()


# import pandas as pd
# import folium
# from folium.plugins import HeatMap
# import streamlit as st
# from streamlit_folium import st_folium

# # Configure the page layout to be wide
# st.set_page_config(layout="wide")

# # Function to load CSV data
# @st.cache_data
# def load_data(glider_file, drone_file):
#     # Load glider data
#     glider_df = pd.read_csv(glider_file)
#     glider_df.columns = ['Unnamed: 0', 'time', 'P2_5', 'unknown', 'P10', 'UV', 'CO', 'Fire', 'H2', 'Temp', 'Hum', 'Lat', 'Long', 'Alt']
    
#     # Convert 'time' column to datetime
#     glider_df['time'] = pd.to_datetime(glider_df['time'], errors='coerce')
    
#     # Load drone data
#     drone_df = pd.read_csv(drone_file, delimiter=';')
#     drone_df.columns = ['Unnamed: 0', 'Timestamp', 'Millis', 'Particles>0.3um', 'Particles>0.5um', 
#                         'Particles>1.0um', 'Particles>2.5um', 'Particles>5.0um', 
#                         'Particles>10.0um', 'PM1.0', 'PM2.5', 'PM10', 'Humidity', 
#                         'Temperature', 'flight_iteration', 'Lat', 'Long', 'Alt']
    
#     # Convert 'Timestamp' to datetime
#     drone_df['Timestamp'] = pd.to_datetime(drone_df['Timestamp'], errors='coerce')
    
#     return glider_df, drone_df

# # Function to create heatmaps
# def add_heatmap(m, data, value_column, gradient):
#     if not data.empty:
#         heat_data = [[row['Lat'], row['Long'], row[value_column]] for _, row in data.iterrows()]
#         HeatMap(data=heat_data, radius=25, blur=15, max_zoom=1, gradient=gradient).add_to(m)

# # Function to generate the legend text to display
# def generate_legend_html(title, color_scale):
#     legend_html = f"""
#     <div style="
#     background-color: white; border:2px solid grey; padding: 10px; font-size:14px;">
#     <h4>{title}</h4>
#     <i style="background: blue; width: 20px; height: 20px; display: inline-block;"></i> Low<br>
#     <i style="background: {color_scale[0.5]}; width: 20px; height: 20px; display: inline-block;"></i> Moderate<br>
#     <i style="background: {color_scale[1.0]}; width: 20px; height: 20px; display: inline-block;"></i> High<br>
#     </div>
#     """
#     return legend_html

# # Function to create Folium map
# @st.cache_data
# def create_map(glider_df, drone_df, selected_iterations, heatmap_opts):
#     # Center the map on Ivanic Grad [45.719999, 16.3418] and set zoom level to 16
#     ivanic_grad_coords = [45.719999, 16.3418]
#     m = folium.Map(location=ivanic_grad_coords, zoom_start=16)

#     # Define common icon color for the pins
#     pin_color = 'orange'
#     symbol_color = 'black'  

#     # Add glider markers
#     if not glider_df.empty:
#         for _, row in glider_df.iterrows():
#             # Create popup content for glider data
#             popup_content = "<strong>Glider Data:</strong><br>"
#             for col in row.index:
#                 popup_content += f"{col}: {row[col]}<br>"
            
#             # Use a custom icon for glider
#             folium.Marker(
#                 location=[row['Lat'], row['Long']],
#                 icon=folium.Icon(color=pin_color, icon='plane', prefix='fa', icon_color=symbol_color),
#                 popup=popup_content
#             ).add_to(m)

#     # Add drone markers
#     if not drone_df.empty:
#         drone_df_filtered = drone_df[drone_df['flight_iteration'].isin(selected_iterations)]
#         for _, row in drone_df_filtered.iterrows():
#             # Create popup content for drone data
#             popup_content = "<strong>Drone Data:</strong><br>"
#             for col in row.index:
#                 popup_content += f"{col}: {row[col]}<br>"
            
#             # Use a custom icon for drone
#             folium.Marker(
#                 location=[row['Lat'], row['Long']],
#                 icon=folium.Icon(color=pin_color, icon='rocket', prefix='fa', icon_color=symbol_color),
#                 popup=popup_content
#             ).add_to(m)

#     # Add humidity heatmap if selected
#     if show_humidity_heatmap:
#         humidity_data = pd.concat([
#             glider_df[['Lat', 'Long', 'Hum']].rename(columns={'Hum': 'Humidity'}),
#             drone_df[['Lat', 'Long', 'Humidity']]
#         ]).dropna()

#         if not humidity_data.empty:
#             heat_data = [[row['Lat'], row['Long'], row['Humidity']] for _, row in humidity_data.iterrows()]
#             HeatMap(data=heat_data, radius=25, blur=15, max_zoom=1,
#                     gradient={0.0: 'blue', 0.5: 'lime', 1.0: 'red'}).add_to(m)

#             # # Add custom legend for the heatmap
#             # legend_html = """
#             # <div style="position: fixed; 
#             #             bottom: 50px; left: 50px; width: 150px; height: 130px; 
#             #             border:2px solid grey; z-index:9999; font-size:14px; 
#             #             background-color: white; opacity: 0.8;">
#             #     <h4 style="text-align: center;">Humidity Legend</h4>
#             #     <i style="background: blue; width: 20px; height: 20px; display: inline-block;"></i> Low<br>
#             #     <i style="background: lime; width: 20px; height: 20px; display: inline-block;"></i> Moderate<br>
#             #     <i style="background: red; width: 20px; height: 20px; display: inline-block;"></i> High<br>
#             # </div>
#             # """
#             # m.get_root().html.add_child(folium.Element(legend_html))

#     # Add temperature heatmap if selected
#     if show_temp_heatmap:
#         temp_data = pd.concat([
#             glider_df[['Lat', 'Long', 'Temp']].rename(columns={'Temp': 'Temperature'}),
#             drone_df[['Lat', 'Long', 'Temperature']]
#         ]).dropna()

#         if not temp_data.empty:
#             heat_data_temp = [[row['Lat'], row['Long'], row['Temperature']] for _, row in temp_data.iterrows()]
#             HeatMap(data=heat_data_temp, radius=25, blur=15, max_zoom=1,
#                     gradient={0.0: 'blue', 0.5: 'yellow', 1.0: 'red'}).add_to(m)

#     # Add PM2.5 heatmap if selected
#     if show_pm25_heatmap:
#         pm25_data = pd.concat([
#             glider_df[['Lat', 'Long', 'P2_5']].rename(columns={'P2_5': 'PM2.5'}),
#             drone_df[['Lat', 'Long', 'PM2.5']]
#         ]).dropna()

#         if not pm25_data.empty:
#             heat_data_pm25 = [[row['Lat'], row['Long'], row['PM2.5']] for _, row in pm25_data.iterrows()]
#             HeatMap(data=heat_data_pm25, radius=25, blur=15, max_zoom=1,
#                     gradient={0.0: 'blue', 0.5: 'yellow', 1.0: 'red'}).add_to(m)

#             # # Add custom legend for PM2.5 heatmap
#             # legend_pm25_html = """
#             # <div style="position: fixed; 
#             #             bottom: 200px; left: 50px; width: 150px; height: 130px; 
#             #             border:2px solid grey; z-index:9999; font-size:14px; 
#             #             background-color: white; opacity: 0.8;">
#             #     <h4 style="text-align: center;">PM2.5 Legend</h4>
#             #     <i style="background: blue; width: 20px; height: 20px; display: inline-block;"></i> Low<br>
#             #     <i style="background: yellow; width: 20px; height: 20px; display: inline-block;"></i> Moderate<br>
#             #     <i style="background: red; width: 20px; height: 20px; display: inline-block;"></i> High<br>
#             # </div>
#             # """
#             # m.get_root().html.add_child(folium.Element(legend_pm25_html))

#      # Add PM5 heatmap if selected
#     if show_pm5_heatmap:
#         pm5_data = pd.concat([
#             glider_df[['Lat', 'Long', 'unknown']].rename(columns={'unknown': 'PM5'})
#         ]).dropna()

#         if not pm5_data.empty:
#             heat_data_pm5 = [[row['Lat'], row['Long'], row['PM5']] for _, row in pm5_data.iterrows()]
#             HeatMap(data=heat_data_pm5, radius=25, blur=15, max_zoom=1,
#                     gradient={0.0: 'blue', 0.5: 'yellow', 1.0: 'red'}).add_to(m)

#             # Add custom legend for PM5 heatmap
#             # legend_pm5_html = """
#             # <div style="position: fixed; 
#             #             bottom: 200px; left: 50px; width: 150px; height: 130px; 
#             #             border:2px solid grey; z-index:9999; font-size:14px; 
#             #             background-color: white; opacity: 0.8;">
#             #     <h4 style="text-align: center;">PM2.5 Legend</h4>
#             #     <i style="background: blue; width: 20px; height: 20px; display: inline-block;"></i> Low<br>
#             #     <i style="background: yellow; width: 20px; height: 20px; display: inline-block;"></i> Moderate<br>
#             #     <i style="background: red; width: 20px; height: 20px; display: inline-block;"></i> High<br>
#             # </div>
#             # """
#             # m.get_root().html.add_child(folium.Element(legend_pm5_html))

#         # Add PM10 heatmap if selected
#     if show_pm10_heatmap:
#         pm10_data = pd.concat([
#             glider_df[['Lat', 'Long', 'P10']].rename(columns={'P10': 'PM10'}),
#             drone_df[['Lat', 'Long', 'PM10']]
#         ]).dropna()

#         if not pm10_data.empty:
#             heat_data_pm10 = [[row['Lat'], row['Long'], row['PM10']] for _, row in pm10_data.iterrows()]
#             HeatMap(data=heat_data_pm10, radius=25, blur=15, max_zoom=1,
#                     gradient={0.0: 'blue', 0.5: 'yellow', 1.0: 'red'}).add_to(m)

#             # # Add custom legend for PM10 heatmap
#             # legend_pm10_html = """
#             # <div style="position: fixed; 
#             #             bottom: 500px; left: 50px; width: 150px; height: 130px; 
#             #             border:2px solid grey; z-index:9999; font-size:14px; 
#             #             background-color: white; opacity: 0.8;">
#             #     <h4 style="text-align: center;">PM10 Legend</h4>
#             #     <i style="background: blue; width: 20px; height: 20px; display: inline-block;"></i> Low<br>
#             #     <i style="background: yellow; width: 20px; height: 20px; display: inline-block;"></i> Moderate<br>
#             #     <i style="background: red; width: 20px; height: 20px; display: inline-block;"></i> High<br>
#             # </div>
#             # """
#             # m.get_root().html.add_child(folium.Element(legend_pm10_html))

#     # Add CO heatmap if selected
#     if show_co_heatmap:
#         co_data = pd.concat([
#             glider_df[['Lat', 'Long', 'CO']].rename(columns={'CO': 'CO'})
#         ]).dropna()

#         if not co_data.empty:
#             heat_data_co = [[row['Lat'], row['Long'], row['CO']] for _, row in co_data.iterrows()]
#             HeatMap(data=heat_data_co, radius=25, blur=15, max_zoom=1,
#                     gradient={0.0: 'blue', 0.5: 'green', 1.0: 'red'}).add_to(m)

#             # # Add custom legend for CO heatmap
#             # legend_co_html = """
#             # <div style="position: fixed; 
#             #             bottom: 350px; left: 50px; width: 150px; height: 130px; 
#             #             border:2px solid grey; z-index:9999; font-size:14px; 
#             #             background-color: white; opacity: 0.8;">
#             #     <h4 style="text-align: center;">CO Legend</h4>
#             #     <i style="background: blue; width: 20px; height: 20px; display: inline-block;"></i> Low<br>
#             #     <i style="background: green; width: 20px; height: 20px; display: inline-block;"></i> Moderate<br>
#             #     <i style="background: red; width: 20px; height: 20px; display: inline-block;"></i> High<br>
#             # </div>
#             # """
#             # m.get_root().html.add_child(folium.Element(legend_co_html))
   
#      # Heatmaps and legends
#     legends = ""
#     if heatmap_opts['humidity']:
#         combined_humidity_data = pd.concat([glider_df[['Lat', 'Long', 'Hum']].rename(columns={'Hum': 'Humidity'}), drone_df[['Lat', 'Long', 'Humidity']]]).dropna()
#         add_heatmap(m, combined_humidity_data, 'Humidity', {0.0: 'blue', 0.5: 'lime', 1.0: 'red'})
#         legends += generate_legend_html("Humidity", {0.5: 'lime', 1.0: 'red'})

#     if heatmap_opts['temp']:
#         combined_temp_data = pd.concat([glider_df[['Lat', 'Long', 'Temp']].rename(columns={'Temp': 'Temperature'}), drone_df[['Lat', 'Long', 'Temperature']]]).dropna()
#         add_heatmap(m, combined_temp_data, 'Temperature', {0.0: 'blue', 0.5: 'yellow', 1.0: 'red'})
#         legends += generate_legend_html("Temperature", {0.5: 'yellow', 1.0: 'red'})

#     if heatmap_opts['pm25']:
#         combined_pm25_data = pd.concat([glider_df[['Lat', 'Long', 'P2_5']].rename(columns={'P2_5': 'PM2.5'}), drone_df[['Lat', 'Long', 'PM2.5']]]).dropna()
#         add_heatmap(m, combined_pm25_data, 'PM2.5', {0.0: 'blue', 0.5: 'yellow', 1.0: 'red'})
#         legends += generate_legend_html("PM2.5", {0.5: 'yellow', 1.0: 'red'})

#     if heatmap_opts['pm10']:
#         combined_pm10_data = pd.concat([glider_df[['Lat', 'Long', 'P10']].rename(columns={'P10': 'PM10'}), drone_df[['Lat', 'Long', 'PM10']]]).dropna()
#         add_heatmap(m, combined_pm10_data, 'PM10', {0.0: 'blue', 0.5: 'yellow', 1.0: 'red'})
#         legends += generate_legend_html("PM10", {0.5: 'yellow', 1.0: 'red'})

#     return m, legends

# # Main function for Streamlit app
# def main():
#     # Specify file paths directly
#     glider_file = '/Users/petra/Desktop/glider.csv'
#     drone_file = '/Users/petra/Desktop/drone.csv'

#     # Load data without uploading
#     glider_data, drone_data = load_data(glider_file, drone_file)

#     # Debugging: Check if data is loaded
#     # st.write("Glider Data Loaded:", glider_data.head())
#     # st.write("Drone Data Loaded:", drone_data.head())

#     # Sidebar for showing markers and selecting flight iterations
#     st.sidebar.subheader("Show Markers")
#     show_all_gliders = st.sidebar.checkbox("Show All Glider Markers", value=True)
#     show_all_drones = st.sidebar.checkbox("Show All Drone Markers", value=True)

#     # Initialize dataframes for filtered data
#     glider_data_to_use = pd.DataFrame()
#     drone_data_to_use = pd.DataFrame()
#     selected_iterations = []

#     # If the checkbox for gliders is checked, display time selector
#     if show_all_gliders:
#         st.sidebar.subheader("Select Time Range for Glider Data")
#         min_time = glider_data['time'].min()
#         max_time = glider_data['time'].max()

#         if pd.isnull(min_time) or pd.isnull(max_time):
#             st.error("Glider time data is missing or invalid. Please check your data.")
#             return

#         selected_time_range = st.sidebar.slider(
#             "Select time range for Glider",
#             min_value=min_time.to_pydatetime(),  
#             max_value=max_time.to_pydatetime(),
#             value=(min_time.to_pydatetime(), max_time.to_pydatetime()),
#             format="YYYY-MM-DD HH:mm"
#         )

#         glider_data_to_use = glider_data[(glider_data['time'] >= selected_time_range[0]) & 
#                                           (glider_data['time'] <= selected_time_range[1])]

#     # If the checkbox for drones is checked, display time selector and flight iteration selection
#     if show_all_drones:
#         st.sidebar.subheader("Select Time Range for Drone Data")
#         min_drone_time = drone_data['Timestamp'].min()
#         max_drone_time = drone_data['Timestamp'].max()

#         if pd.isnull(min_drone_time) or pd.isnull(max_drone_time):
#             st.error("Drone time data is missing or invalid. Please check your data.")
#             return

#         selected_drone_time_range = st.sidebar.slider(
#             "Select time range for Drone",
#             min_value=min_drone_time.to_pydatetime(),  
#             max_value=max_drone_time.to_pydatetime(),
#             value=(min_drone_time.to_pydatetime(), max_drone_time.to_pydatetime()),
#             format="YYYY-MM-DD HH:mm"
#         )

#         drone_data_filtered = drone_data[(drone_data['Timestamp'] >= selected_drone_time_range[0]) & 
#                                           (drone_data['Timestamp'] <= selected_drone_time_range[1])]
#         drone_data_to_use = drone_data_filtered

#         # Select flight iterations to show
#         flight_iterations = drone_data['flight_iteration'].unique()
#         selected_iterations = st.sidebar.multiselect(
#             "Select Flight Iterations to Display",
#             options=flight_iterations,
#             default=flight_iterations.tolist()  # Default to all iterations
#         )

#     # Heatmap options
#     st.sidebar.subheader("Heatmap Options")
#     # show_humidity_heatmap = st.sidebar.checkbox("Show Humidity Heatmap", value=False)
#     # show_temp_heatmap = st.sidebar.checkbox("Show Temperature Heatmap", value=False)
#     # show_pm25_heatmap = st.sidebar.checkbox("Show PM2.5 Heatmap", value=False)
#     # show_pm5_heatmap = st.sidebar.checkbox("Show PM5 Heatmap", value=False)
#     # show_pm10_heatmap = st.sidebar.checkbox("Show PM10 Heatmap", value=False)
#     # show_co_heatmap = st.sidebar.checkbox("Show CO Heatmap", value=False)
#     heatmap_opts = {opt: st.sidebar.checkbox(f"Show {opt.capitalize()} Heatmap", value=False) for opt in ['humidity', 'temp', 'pm25', 'pm10']}


#     # Create the map
#     # if show_all_gliders or show_all_drones:
#         # st.subheader("Combined Glider and Drone Data Map")
#         # Combine filtered data
#     combined_glider_data = glider_data_to_use
#     combined_drone_data = drone_data_to_use
        
#         # Debugging: Check if there is any data to show
#         # st.write("Filtered Glider Data:", combined_glider_data)
#         # st.write("Filtered Drone Data:", combined_drone_data)

#         # Only show markers if there's data
#     if not combined_glider_data.empty or not combined_drone_data.empty:
#         map_, legends = create_map(combined_glider_data, combined_drone_data, selected_iterations, heatmap_opts)
#         st_folium(map_, width=700, height=500)
#     else:
#         st.warning("No data available for the selected filters.")

# # Run the main function
# if __name__ == "__main__":
#     main()


# import pandas as pd
# import folium
# from folium.plugins import HeatMap
# import streamlit as st
# from streamlit_folium import st_folium

# # Configure the page layout to be wide
# st.set_page_config(layout="wide")

# # Function to load CSV data
# @st.cache_data
# def load_data(glider_file, drone_file):
#     # Load glider data
#     glider_df = pd.read_csv(glider_file)
#     glider_df.columns = ['Unnamed: 0', 'time', 'P2_5', 'unknown', 'P10', 'UV', 'CO', 'Fire', 'H2', 'Temp', 'Hum', 'Lat', 'Long', 'Alt']
    
#     # Convert 'time' column to datetime
#     glider_df['time'] = pd.to_datetime(glider_df['time'], errors='coerce')
    
#     # Load drone data
#     drone_df = pd.read_csv(drone_file, delimiter=';')
#     drone_df.columns = ['Unnamed: 0', 'Timestamp', 'Millis', 'Particles>0.3um', 'Particles>0.5um', 
#                         'Particles>1.0um', 'Particles>2.5um', 'Particles>5.0um', 
#                         'Particles>10.0um', 'PM1.0', 'PM2.5', 'PM10', 'Humidity', 
#                         'Temperature', 'flight_iteration', 'Lat', 'Long', 'Alt']
    
#     # Convert 'Timestamp' to datetime
#     drone_df['Timestamp'] = pd.to_datetime(drone_df['Timestamp'], errors='coerce')
    
#     return glider_df, drone_df

# # Function to create Folium map
# @st.cache_data
# def create_map(glider_df, drone_df, show_humidity_heatmap, show_temp_heatmap, selected_iterations):
#     # Center the map on Ivanic Grad [45.719999, 16.3418] and set zoom level to 16
#     ivanic_grad_coords = [45.719999, 16.3418]
#     m = folium.Map(location=ivanic_grad_coords, zoom_start=16)

#     # Define common icon color for the pins
#     pin_color = 'orange'
#     symbol_color = 'black'  

#     # Add glider markers
#     if not glider_df.empty:
#         for _, row in glider_df.iterrows():
#             # Create popup content for glider data
#             popup_content = "<strong>Glider Data:</strong><br>"
#             for col in row.index:
#                 popup_content += f"{col}: {row[col]}<br>"
            
#             # Use a custom icon for glider
#             folium.Marker(
#                 location=[row['Lat'], row['Long']],
#                 icon=folium.Icon(color=pin_color, icon='plane', prefix='fa', icon_color=symbol_color),
#                 popup=popup_content
#             ).add_to(m)

#     # Add drone markers
#     if not drone_df.empty:
#         drone_df_filtered = drone_df[drone_df['flight_iteration'].isin(selected_iterations)]
#         for _, row in drone_df_filtered.iterrows():
#             # Create popup content for drone data
#             popup_content = "<strong>Drone Data:</strong><br>"
#             for col in row.index:
#                 popup_content += f"{col}: {row[col]}<br>"
            
#             # Use a custom icon for drone
#             folium.Marker(
#                 location=[row['Lat'], row['Long']],
#                 icon=folium.Icon(color=pin_color, icon='rocket', prefix='fa', icon_color=symbol_color),
#                 popup=popup_content
#             ).add_to(m)

#     # Add humidity heatmap if selected
#     if show_humidity_heatmap:
#         humidity_data = pd.concat([
#             glider_df[['Lat', 'Long', 'Hum']].rename(columns={'Hum': 'Humidity'}),
#             drone_df[['Lat', 'Long', 'Humidity']]
#         ]).dropna()

#         if not humidity_data.empty:
#             heat_data = [[row['Lat'], row['Long'], row['Humidity']] for _, row in humidity_data.iterrows()]
#             HeatMap(data=heat_data, radius=25, blur=15, max_zoom=1,
#                     gradient={0.0: 'blue', 0.5: 'lime', 1.0: 'red'}).add_to(m)

#             # Add custom legend for the heatmap
#             legend_html = """
#             <div style="position: fixed; 
#                         bottom: 50px; left: 50px; width: 150px; height: 130px; 
#                         border:2px solid grey; z-index:9999; font-size:14px; 
#                         background-color: white; opacity: 0.8;">
#                 <h4 style="text-align: center;">Humidity Legend</h4>
#                 <i style="background: blue; width: 20px; height: 20px; display: inline-block;"></i> Low<br>
#                 <i style="background: lime; width: 20px; height: 20px; display: inline-block;"></i> Moderate<br>
#                 <i style="background: red; width: 20px; height: 20px; display: inline-block;"></i> High<br>
#             </div>
#             """
#             m.get_root().html.add_child(folium.Element(legend_html))

#     # Add temperature heatmap if selected
#     if show_temp_heatmap:
#         temp_data = pd.concat([
#             glider_df[['Lat', 'Long', 'Temp']].rename(columns={'Temp': 'Temperature'}),
#             drone_df[['Lat', 'Long', 'Temperature']]
#         ]).dropna()

#         if not temp_data.empty:
#             heat_data_temp = [[row['Lat'], row['Long'], row['Temperature']] for _, row in temp_data.iterrows()]
#             HeatMap(data=heat_data_temp, radius=25, blur=15, max_zoom=1,
#                     gradient={0.0: 'blue', 0.5: 'yellow', 1.0: 'red'}).add_to(m)

#     # Add layer control
#     folium.LayerControl().add_to(m)
    
#     return m

# # Streamlit app
# def main():
#     # Specify file paths directly
#     glider_file = '/Users/petra/Desktop/glider.csv'
#     drone_file = '/Users/petra/Desktop/drone.csv'

#     # Load data without uploading
#     glider_data, drone_data = load_data(glider_file, drone_file)
    
#     # Sidebar for showing markers and selecting flight iterations
#     st.sidebar.subheader("Show Markers")
#     show_all_gliders = st.sidebar.checkbox("Show All Glider Markers", value=False)
#     show_all_drones = st.sidebar.checkbox("Show All Drone Markers", value=False)

#     # Initialize dataframes for filtered data
#     glider_data_to_use = pd.DataFrame()
#     drone_data_to_use = pd.DataFrame()
#     selected_iterations = []

#     # If the checkbox for gliders is checked, display time selector
#     if show_all_gliders:
#         st.sidebar.subheader("Select Time Range for Glider Data")
#         min_time = glider_data['time'].min()
#         max_time = glider_data['time'].max()

#         if pd.isnull(min_time) or pd.isnull(max_time):
#             st.error("Glider time data is missing or invalid. Please check your data.")
#             return
        
#         selected_time_range = st.sidebar.slider(
#             "Select time range for Glider",
#             min_value=min_time.to_pydatetime(),  
#             max_value=max_time.to_pydatetime(),
#             value=(min_time.to_pydatetime(), max_time.to_pydatetime()),
#             format="YYYY-MM-DD HH:mm"
#         )

#         glider_data_to_use = glider_data[(glider_data['time'] >= selected_time_range[0]) & 
#                                           (glider_data['time'] <= selected_time_range[1])]

#     # If the checkbox for drones is checked, display time selector and flight iteration selection
#     if show_all_drones:
#         st.sidebar.subheader("Select Time Range for Drone Data")
#         min_drone_time = drone_data['Timestamp'].min()
#         max_drone_time = drone_data['Timestamp'].max()

#         if pd.isnull(min_drone_time) or pd.isnull(max_drone_time):
#             st.error("Drone time data is missing or invalid. Please check your data.")
#             return
        
#         selected_drone_time_range = st.sidebar.slider(
#             "Select time range for Drone",
#             min_value=min_drone_time.to_pydatetime(),  
#             max_value=max_drone_time.to_pydatetime(),
#             value=(min_drone_time.to_pydatetime(), max_drone_time.to_pydatetime()),
#             format="YYYY-MM-DD HH:mm"
#         )

#         drone_data_filtered = drone_data[(drone_data['Timestamp'] >= selected_drone_time_range[0]) & 
#                                           (drone_data['Timestamp'] <= selected_drone_time_range[1])]
#         drone_data_to_use = drone_data_filtered

#         # Select flight iterations to show
#         flight_iterations = drone_data['flight_iteration'].unique()
#         selected_iterations = st.sidebar.multiselect(
#             "Select Flight Iterations to Display",
#             options=flight_iterations,
#             default=flight_iterations.tolist()  # Default to all iterations
#         )

#     # Heatmap options
#     st.sidebar.subheader("Heatmap Options")
#     show_humidity_heatmap = st.sidebar.checkbox("Show Humidity Heatmap", value=False)
#     show_temp_heatmap = st.sidebar.checkbox("Show Temperature Heatmap", value=False)

#     # Create the map
#     if show_all_gliders or show_all_drones:
#         st.subheader("Combined Glider and Drone Data Map")
#         # Combine filtered data
#         combined_glider_data = glider_data_to_use
#         combined_drone_data = drone_data_to_use
        
#         # Only show markers if there's data
#         if not combined_glider_data.empty or not combined_drone_data.empty:
#             map_ = create_map(combined_glider_data, combined_drone_data, show_humidity_heatmap, show_temp_heatmap, selected_iterations)
#             st_folium(map_, width=700, height=500)
#         else:
#             st.warning("No data available for the selected filters.")

# if __name__ == "__main__":
#     main()



# import pandas as pd
# import folium
# from folium.plugins import HeatMap
# import streamlit as st
# from streamlit_folium import st_folium

# # Configure the page layout to be wide
# st.set_page_config(layout="wide")

# # Function to load CSV data
# @st.cache_data
# def load_data(glider_file, drone_file):
#     # Load glider data
#     glider_df = pd.read_csv(glider_file)
#     glider_df.columns = ['Unnamed: 0', 'time', 'P2_5', 'unknown', 'P10', 'UV', 'CO', 'Fire', 'H2', 'Temp', 'Hum', 'Lat', 'Long', 'Alt']
    
#     # Convert 'time' column to datetime
#     glider_df['time'] = pd.to_datetime(glider_df['time'], errors='coerce')
    
#     # Load drone data
#     drone_df = pd.read_csv(drone_file, delimiter=';')
#     drone_df.columns = ['Unnamed: 0', 'Timestamp', 'Millis', 'Particles>0.3um', 'Particles>0.5um', 
#                         'Particles>1.0um', 'Particles>2.5um', 'Particles>5.0um', 
#                         'Particles>10.0um', 'PM1.0', 'PM2.5', 'PM10', 'Humidity', 
#                         'Temperature', 'flight_iteration', 'Lat', 'Long', 'Alt']
    
#     # Convert 'Timestamp' to datetime
#     drone_df['Timestamp'] = pd.to_datetime(drone_df['Timestamp'], errors='coerce')
    
#     return glider_df, drone_df

# # Function to create Folium map
# @st.cache_data
# def create_map(glider_df, drone_df, show_humidity_heatmap, show_temp_heatmap, selected_iterations):
#     # Center the map on Ivanic Grad [45.719999, 16.3418] and set zoom level to 16
#     ivanic_grad_coords = [45.719999, 16.3418]
#     m = folium.Map(location=ivanic_grad_coords, zoom_start=16)

#     # Define common icon color for the pins
#     pin_color = 'orange'
#     symbol_color = 'black'  

#     # Add glider markers
#     if not glider_df.empty:
#         for _, row in glider_df.iterrows():
#             # Create popup content for glider data
#             popup_content = "<strong>Glider Data:</strong><br>"
#             for col in row.index:
#                 popup_content += f"{col}: {row[col]}<br>"
            
#             # Use a custom icon for glider
#             folium.Marker(
#                 location=[row['Lat'], row['Long']],
#                 icon=folium.Icon(color=pin_color, icon='plane', prefix='fa', icon_color=symbol_color),
#                 popup=popup_content
#             ).add_to(m)

#     # Add drone markers
#     if not drone_df.empty:
#         drone_df_filtered = drone_df[drone_df['flight_iteration'].isin(selected_iterations)]
#         for _, row in drone_df_filtered.iterrows():
#             # Create popup content for drone data
#             popup_content = "<strong>Drone Data:</strong><br>"
#             for col in row.index:
#                 popup_content += f"{col}: {row[col]}<br>"
            
#             # Use a custom icon for drone
#             folium.Marker(
#                 location=[row['Lat'], row['Long']],
#                 icon=folium.Icon(color=pin_color, icon='rocket', prefix='fa', icon_color=symbol_color),
#                 popup=popup_content
#             ).add_to(m)

#     # Add humidity heatmap if selected
#     if show_humidity_heatmap:
#         humidity_data = pd.concat([
#             glider_df[['Lat', 'Long', 'Hum']].rename(columns={'Hum': 'Humidity'}),
#             drone_df[['Lat', 'Long', 'Humidity']]
#         ]).dropna()

#         if not humidity_data.empty:
#             heat_data = [[row['Lat'], row['Long'], row['Humidity']] for _, row in humidity_data.iterrows()]
#             HeatMap(data=heat_data, radius=25, blur=15, max_zoom=1,
#                     gradient={0.0: 'blue', 0.5: 'lime', 1.0: 'red'}).add_to(m)

#             # Add custom legend for the heatmap
#             legend_html = """
#             <div style="position: fixed; 
#                         bottom: 50px; left: 50px; width: 150px; height: 130px; 
#                         border:2px solid grey; z-index:9999; font-size:14px; 
#                         background-color: white; opacity: 0.8;">
#                 <h4 style="text-align: center;">Humidity Legend</h4>
#                 <i style="background: blue; width: 20px; height: 20px; display: inline-block;"></i> Low<br>
#                 <i style="background: lime; width: 20px; height: 20px; display: inline-block;"></i> Moderate<br>
#                 <i style="background: red; width: 20px; height: 20px; display: inline-block;"></i> High<br>
#             </div>
#             """
#             m.get_root().html.add_child(folium.Element(legend_html))

#     # Add temperature heatmap if selected
#     if show_temp_heatmap:
#         temp_data = pd.concat([
#             glider_df[['Lat', 'Long', 'Temp']].rename(columns={'Temp': 'Temperature'}),
#             drone_df[['Lat', 'Long', 'Temperature']]
#         ]).dropna()

#         if not temp_data.empty:
#             heat_data_temp = [[row['Lat'], row['Long'], row['Temperature']] for _, row in temp_data.iterrows()]
#             HeatMap(data=heat_data_temp, radius=25, blur=15, max_zoom=1,
#                     gradient={0.0: 'blue', 0.5: 'yellow', 1.0: 'red'}).add_to(m)

#     # Add layer control
#     folium.LayerControl().add_to(m)
    
#     return m

# # Streamlit app
# def main():
#     # Specify file paths directly
#     glider_file = '/Users/petra/Desktop/glider.csv'
#     drone_file = '/Users/petra/Desktop/drone.csv'

#     # Load data without uploading
#     glider_data, drone_data = load_data(glider_file, drone_file)
    
#     # Sidebar for showing markers and selecting flight iterations
#     st.sidebar.subheader("Show Markers")
#     show_all_gliders = st.sidebar.checkbox("Show All Glider Markers", value=False)
#     show_all_drones = st.sidebar.checkbox("Show All Drone Markers", value=False)

#     # Initialize dataframes for filtered data
#     glider_data_to_use = pd.DataFrame()
#     drone_data_to_use = pd.DataFrame()
#     selected_iterations = []

#     # If the checkbox for gliders is checked, display time selector
#     if show_all_gliders:
#         st.sidebar.subheader("Select Time Range for Glider Data")
#         min_time = glider_data['time'].min()
#         max_time = glider_data['time'].max()

#         if pd.isnull(min_time) or pd.isnull(max_time):
#             st.error("Glider time data is missing or invalid. Please check your data.")
#             return
        
#         selected_time_range = st.sidebar.slider(
#             "Select time range for Glider",
#             min_value=min_time.to_pydatetime(),  
#             max_value=max_time.to_pydatetime(),
#             value=(min_time.to_pydatetime(), max_time.to_pydatetime()),
#             format="YYYY-MM-DD HH:mm"
#         )

#         glider_data_to_use = glider_data[(glider_data['time'] >= selected_time_range[0]) & 
#                                           (glider_data['time'] <= selected_time_range[1])]

#     # If the checkbox for drones is checked, display time selector and flight iteration selection
#     if show_all_drones:
#         st.sidebar.subheader("Select Time Range for Drone Data")
#         min_drone_time = drone_data['Timestamp'].min()
#         max_drone_time = drone_data['Timestamp'].max()

#         if pd.isnull(min_drone_time) or pd.isnull(max_drone_time):
#             st.error("Drone time data is missing or invalid. Please check your data.")
#             return
        
#         selected_drone_time_range = st.sidebar.slider(
#             "Select time range for Drone",
#             min_value=min_drone_time.to_pydatetime(),  
#             max_value=max_drone_time.to_pydatetime(),
#             value=(min_drone_time.to_pydatetime(), max_drone_time.to_pydatetime()),
#             format="YYYY-MM-DD HH:mm"
#         )

#         drone_data_filtered = drone_data[(drone_data['Timestamp'] >= selected_drone_time_range[0]) & 
#                                           (drone_data['Timestamp'] <= selected_drone_time_range[1])]
#         drone_data_to_use = drone_data_filtered

#         # Select flight iterations to show
#         flight_iterations = drone_data['flight_iteration'].unique()
#         selected_iterations = st.sidebar.multiselect(
#             "Select Flight Iterations to Display",
#             options=flight_iterations,
#             default=flight_iterations.tolist()  # Default to all iterations
#         )

#     # Heatmap options
#     st.sidebar.subheader("Heatmap Options")
#     show_humidity_heatmap = st.sidebar.checkbox("Show Humidity Heatmap", value=False)
#     show_temp_heatmap = st.sidebar.checkbox("Show Temperature Heatmap", value=False)

#     # Create the map
#     if show_all_gliders or show_all_drones:
#         if show_all_gliders:
#             st.subheader("Glider Data Map")
#             map_ = create_map(glider_data_to_use, drone_data_to_use, show_humidity_heatmap, show_temp_heatmap, selected_iterations)
#             st_folium(map_, width=700, height=500)
        
#         if show_all_drones:
#             st.subheader("Drone Data Map")
#             map_ = create_map(glider_data_to_use, drone_data_to_use, show_humidity_heatmap, show_temp_heatmap, selected_iterations)
#             st_folium(map_, width=700, height=500)

# if __name__ == "__main__":
#     main()


# import pandas as pd
# import folium
# from folium.plugins import HeatMap
# import streamlit as st
# from streamlit_folium import st_folium

# # Configure the page layout to be wide
# st.set_page_config(layout="wide")

# # Function to load CSV data
# @st.cache_data
# def load_data(glider_file, drone_file):
#     # Load glider data
#     glider_df = pd.read_csv(glider_file)
#     glider_df.columns = ['Unnamed: 0', 'time', 'P2_5', 'unknown', 'P10', 'UV', 'CO', 'Fire', 'H2', 'Temp', 'Hum', 'Lat', 'Long', 'Alt']
    
#     # Convert 'time' column to datetime
#     glider_df['time'] = pd.to_datetime(glider_df['time'], errors='coerce')
    
#     # Load drone data
#     drone_df = pd.read_csv(drone_file, delimiter=';')
#     drone_df.columns = ['Unnamed: 0', 'Timestamp', 'Millis', 'Particles>0.3um', 'Particles>0.5um', 
#                         'Particles>1.0um', 'Particles>2.5um', 'Particles>5.0um', 
#                         'Particles>10.0um', 'PM1.0', 'PM2.5', 'PM10', 'Humidity', 
#                         'Temperature', 'flight_iteration', 'Lat', 'Long', 'Alt']
    
#     # Convert 'Timestamp' to datetime
#     drone_df['Timestamp'] = pd.to_datetime(drone_df['Timestamp'], errors='coerce')
    
#     return glider_df, drone_df

# # Function to create Folium map
# @st.cache_data  # Cache the map creation to avoid re-rendering
# # Function to create Folium map
# @st.cache_data  # Cache the map creation to avoid re-rendering
# def create_map(glider_df, drone_df, show_humidity_heatmap, show_temp_heatmap):
#     # Center the map on Ivanic Grad [45.719999, 16.3418] and set zoom level to 16
#     ivanic_grad_coords = [45.719999, 16.3418]
#     m = folium.Map(location=ivanic_grad_coords, zoom_start=16)

#     # Define common icon color for the pins (orange pin and black symbol)
#     pin_color = 'orange'
#     symbol_color = 'black'  # Set the icon (symbol) color to black

#     # Add glider markers
#     if not glider_df.empty:  # Only add markers if the dataframe is not empty
#         for _, row in glider_df.iterrows():
#             # Create popup content for glider data (show all info)
#             popup_content = "<strong>Glider Data:</strong><br>"
#             for col in row.index:
#                 popup_content += f"{col}: {row[col]}<br>"
            
#             # Use a custom icon for glider without shadow
#             folium.Marker(
#                 location=[row['Lat'], row['Long']],
#                 icon=folium.Icon(color=pin_color, icon='plane', prefix='fa', icon_color=symbol_color, shadow=False),
#                 popup=popup_content
#             ).add_to(m)

#     # Add drone markers
#     if not drone_df.empty:  # Only add markers if the dataframe is not empty
#         for _, row in drone_df.iterrows():
#             # Create popup content for drone data (show all info)
#             popup_content = "<strong>Drone Data:</strong><br>"
#             for col in row.index:
#                 popup_content += f"{col}: {row[col]}<br>"
            
#             # Use a custom icon for drone without shadow
#             folium.Marker(
#                 location=[row['Lat'], row['Long']],
#                 icon=folium.Icon(color=pin_color, icon='rocket', prefix='fa', icon_color=symbol_color, shadow=False),
#                 popup=popup_content
#             ).add_to(m)

#     # Add heatmap for humidity data if the user wants to see it and data is available
#     if show_humidity_heatmap:
#         # Check if the relevant columns are in the glider and drone DataFrames
#         if 'Lat' in glider_df.columns and 'Long' in glider_df.columns and 'Hum' in glider_df.columns:
#             humidity_data = glider_df[['Lat', 'Long', 'Hum']].rename(columns={'Hum': 'Humidity'})
#         else:
#             humidity_data = pd.DataFrame(columns=['Lat', 'Long', 'Humidity'])

#         if 'Lat' in drone_df.columns and 'Long' in drone_df.columns and 'Humidity' in drone_df.columns:
#             humidity_data = pd.concat([
#                 humidity_data,
#                 drone_df[['Lat', 'Long', 'Humidity']]
#             ])
        
#         # Drop rows with NaN values
#         humidity_data = humidity_data.dropna()
        
#         # Create heat data
#         if not humidity_data.empty:
#             heat_data = [[row['Lat'], row['Long'], row['Humidity']] for _, row in humidity_data.iterrows()]

#             # Modify HeatMap parameters for smoother effect
#             HeatMap(data=heat_data, radius=25, blur=15, max_zoom=1, 
#                     gradient={0.0: 'blue', 0.5: 'lime', 1.0: 'red'}).add_to(m)

#             # Add custom legend for the heatmap
#             legend_html = """
#             <div style="position: fixed; 
#                         bottom: 50px; left: 50px; width: 150px; height: 130px; 
#                         border:2px solid grey; z-index:9999; font-size:14px; 
#                         background-color: white; opacity: 0.8;">
#                 <h4 style="text-align: center;">Humidity Legend</h4>
#                 <i style="background: blue; width: 20px; height: 20px; display: inline-block;"></i> Low<br>
#                 <i style="background: lime; width: 20px; height: 20px; display: inline-block;"></i> Moderate<br>
#                 <i style="background: red; width: 20px; height: 20px; display: inline-block;"></i> High<br>
#             </div>
#             """
#             m.get_root().html.add_child(folium.Element(legend_html))

#     # Add combined heatmap for glider and drone temperature data if selected
#     if show_temp_heatmap:
#         # Combine temperature data from both datasets only if the relevant columns are available
#         temp_data = pd.DataFrame(columns=['Lat', 'Long', 'Temperature'])

#         if 'Lat' in glider_df.columns and 'Long' in glider_df.columns and 'Temp' in glider_df.columns:
#             temp_data = pd.concat([
#                 temp_data,
#                 glider_df[['Lat', 'Long', 'Temp']].rename(columns={'Temp': 'Temperature'})
#             ])

#         if 'Lat' in drone_df.columns and 'Long' in drone_df.columns and 'Temperature' in drone_df.columns:
#             temp_data = pd.concat([
#                 temp_data,
#                 drone_df[['Lat', 'Long', 'Temperature']]
#             ])
        
#         # Drop rows with NaN values
#         temp_data = temp_data.dropna()

#         # Add temperature heatmap if there is data
#         if not temp_data.empty:
#             heat_data_temp = [[row['Lat'], row['Long'], row['Temperature']] for _, row in temp_data.iterrows()]

#             # Add temperature heatmap
#             HeatMap(data=heat_data_temp, radius=25, blur=15, max_zoom=1, 
#                     gradient={0.0: 'blue', 0.5: 'yellow', 1.0: 'red'}).add_to(m)

#     # Add layer control
#     folium.LayerControl().add_to(m)
    
#     return m

#     # Center the map on Ivanic Grad [45.719999, 16.3418] and set zoom level to 16
#     ivanic_grad_coords = [45.719999, 16.3418]
#     m = folium.Map(location=ivanic_grad_coords, zoom_start=16)

#     # Define common icon color for the pins (orange pin and black symbol)
#     pin_color = 'orange'
#     symbol_color = 'black'  # Set the icon (symbol) color to black

#     # Add glider markers
#     if not glider_df.empty:  # Only add markers if the dataframe is not empty
#         for _, row in glider_df.iterrows():
#             # Create popup content for glider data (show all info)
#             popup_content = "<strong>Glider Data:</strong><br>"
#             for col in row.index:
#                 popup_content += f"{col}: {row[col]}<br>"
            
#             # Use a custom icon for glider without shadow
#             folium.Marker(
#                 location=[row['Lat'], row['Long']],
#                 icon=folium.Icon(color=pin_color, icon='plane', prefix='fa', icon_color=symbol_color, shadow=False),
#                 popup=popup_content
#             ).add_to(m)

#     # Add drone markers
#     if not drone_df.empty:  # Only add markers if the dataframe is not empty
#         for _, row in drone_df.iterrows():
#             # Create popup content for drone data (show all info)
#             popup_content = "<strong>Drone Data:</strong><br>"
#             for col in row.index:
#                 popup_content += f"{col}: {row[col]}<br>"
            
#             # Use a custom icon for drone without shadow
#             folium.Marker(
#                 location=[row['Lat'], row['Long']],
#                 icon=folium.Icon(color=pin_color, icon='rocket', prefix='fa', icon_color=symbol_color, shadow=False),
#                 popup=popup_content
#             ).add_to(m)

#     # Add heatmap for humidity data if the user wants to see it
#     if show_humidity_heatmap:
#         # Combine humidity data from both datasets
#         humidity_data = pd.concat([
#             glider_df[['Lat', 'Long', 'Hum']].rename(columns={'Hum': 'Humidity'}),
#             drone_df[['Lat', 'Long', 'Humidity']]
#         ]).dropna()
        
#         # Create heat data
#         heat_data = [[row['Lat'], row['Long'], row['Humidity']] for _, row in humidity_data.iterrows()]

#         # Modify HeatMap parameters for smoother effect
#         HeatMap(data=heat_data, radius=25, blur=15, max_zoom=1, 
#                 gradient={0.0: 'blue', 0.5: 'lime', 1.0: 'red'}).add_to(m)

#         # Add custom legend for the heatmap
#         legend_html = """
#         <div style="position: fixed; 
#                     bottom: 50px; left: 50px; width: 150px; height: 130px; 
#                     border:2px solid grey; z-index:9999; font-size:14px; 
#                     background-color: white; opacity: 0.8;">
#             <h4 style="text-align: center;">Humidity Legend</h4>
#             <i style="background: blue; width: 20px; height: 20px; display: inline-block;"></i> Low<br>
#             <i style="background: lime; width: 20px; height: 20px; display: inline-block;"></i> Moderate<br>
#             <i style="background: red; width: 20px; height: 20px; display: inline-block;"></i> High<br>
#         </div>
#         """
#         m.get_root().html.add_child(folium.Element(legend_html))

#     # Add combined heatmap for glider and drone temperature data if selected
#     if show_temp_heatmap:
#         # Combine temperature data from both datasets
#         temp_data = pd.concat([
#             glider_df[['Lat', 'Long', 'Temp']].rename(columns={'Temp': 'Temperature'}),
#             drone_df[['Lat', 'Long', 'Temperature']]
#         ]).dropna()
        
#         # Create heat data
#         heat_data_temp = [[row['Lat'], row['Long'], row['Temperature']] for _, row in temp_data.iterrows()]

#         # Add temperature heatmap
#         HeatMap(data=heat_data_temp, radius=25, blur=15, max_zoom=1, 
#                 gradient={0.0: 'blue', 0.5: 'yellow', 1.0: 'red'}).add_to(m)

#     # Add layer control
#     folium.LayerControl().add_to(m)
    
#     return m

# # Streamlit app
# def main():
#     # Specify file paths directly
#     glider_file = '/Users/petra/Desktop/glider.csv'
#     drone_file = '/Users/petra/Desktop/drone.csv'

#     # Load data without uploading
#     glider_data, drone_data = load_data(glider_file, drone_file)
    
#     # Sidebar checkboxes for showing all markers
#     st.sidebar.subheader("Show Markers")
#     show_all_gliders = st.sidebar.checkbox("Show All Glider Markers", value=False)
#     show_all_drones = st.sidebar.checkbox("Show All Drone Markers", value=False)

#     # Initialize dataframes to be empty by default
#     glider_data_to_use = pd.DataFrame()
#     drone_data_to_use = pd.DataFrame()

#     # If the checkbox for gliders is checked, display time selector
#     if show_all_gliders:
#         st.sidebar.subheader("Select Time Range for Glider Data")
#         min_time = glider_data['time'].min()
#         max_time = glider_data['time'].max()

#         # Ensure that the time range is correctly recognized as datetime
#         if pd.isnull(min_time) or pd.isnull(max_time):
#             st.error("Glider time data is missing or invalid. Please check your data.")
#             return
        
#         selected_time_range = st.sidebar.slider(
#             "Select time range for Glider",
#             min_value=min_time.to_pydatetime(),  
#             max_value=max_time.to_pydatetime(),
#             value=(min_time.to_pydatetime(), max_time.to_pydatetime()),
#             format="YYYY-MM-DD HH:mm",
#             key="glider_time_slider"  # Unique key for Glider time range slider
#         )

#         # Filter glider data by selected time range
#         glider_data_filtered = glider_data[(glider_data['time'] >= selected_time_range[0]) & 
#                                             (glider_data['time'] <= selected_time_range[1])]

#         # Use filtered glider data for the map
#         glider_data_to_use = glider_data_filtered

#     # If the checkbox for drones is checked, display time selector
#     if show_all_drones:
#         st.sidebar.subheader("Select Time Range for Drone Data")
#         min_drone_time = drone_data['Timestamp'].min()
#         max_drone_time = drone_data['Timestamp'].max()

#         # Ensure that the time range is correctly recognized as datetime
#         if pd.isnull(min_drone_time) or pd.isnull(max_drone_time):
#             st.error("Drone time data is missing or invalid. Please check your data.")
#             return
        
#         selected_drone_time_range = st.sidebar.slider(
#             "Select time range for Drone",
#             min_value=min_drone_time.to_pydatetime(),  
#             max_value=max_drone_time.to_pydatetime(),
#             value=(min_drone_time.to_pydatetime(), max_drone_time.to_pydatetime()),
#             format="YYYY-MM-DD HH:mm",
#             key="drone_time_slider"  # Unique key for Drone time range slider
#         )

#         # Filter drone data by selected time range
#         drone_data_filtered = drone_data[(drone_data['Timestamp'] >= selected_drone_time_range[0]) & 
#                                           (drone_data['Timestamp'] <= selected_drone_time_range[1])]

#         # Use filtered drone data for the map
#         drone_data_to_use = drone_data_filtered

#     # Checkboxes for heatmaps
#     st.sidebar.subheader("Show Heatmaps")
#     show_humidity_heatmap = st.sidebar.checkbox("Show Humidity Heatmap", value=False)
#     show_temp_heatmap = st.sidebar.checkbox("Show Temperature Heatmap", value=False)

#     # Create the map with the selected data
#     map_ = create_map(glider_data_to_use, drone_data_to_use, show_humidity_heatmap, show_temp_heatmap)

#     # Display the map
#     st_folium(map_, width=725)

# # Run the app
# if __name__ == "__main__":
#     main()









# import pandas as pd
# import folium
# from folium.plugins import HeatMap
# import streamlit as st
# from streamlit_folium import st_folium
# import seaborn as sns
# import matplotlib.pyplot as plt
# import random

# # Configure the page layout to be wide
# st.set_page_config(layout="wide")

# # Function to load CSV data
# @st.cache_data
# def load_data(glider_file, drone_file):
#     # Load glider data
#     glider_df = pd.read_csv(glider_file)
#     glider_df.columns = ['Unnamed: 0', 'time', 'P2_5', 'unknown', 'P10', 'UV', 'CO', 'Fire', 'H2', 'Temp', 'Hum', 'Lat', 'Long', 'Alt']
    
#     # Convert 'time' column to datetime
#     glider_df['time'] = pd.to_datetime(glider_df['time'], errors='coerce')
    
#     # Load drone data
#     drone_df = pd.read_csv(drone_file, delimiter=';')
#     drone_df.columns = ['Unnamed: 0', 'Timestamp', 'Millis', 'Particles>0.3um', 'Particles>0.5um', 
#                         'Particles>1.0um', 'Particles>2.5um', 'Particles>5.0um', 
#                         'Particles>10.0um', 'PM1.0', 'PM2.5', 'PM10', 'Humidity', 
#                         'Temperature', 'flight_iteration', 'Lat', 'Long', 'Alt']
    
#     # Convert 'Timestamp' to datetime
#     drone_df['Timestamp'] = pd.to_datetime(drone_df['Timestamp'], errors='coerce')
    
#     return glider_df, drone_df

# # Function to create Folium map
# @st.cache_data  # Cache the map creation to avoid re-rendering
# def create_map(glider_df, drone_df, selected_glider_layers, selected_drone_layers, show_humidity_heatmap, show_temp_heatmap):
#     # Center the map on Ivanic Grad [45.719999, 16.3418] and set zoom level to 16
#     ivanic_grad_coords = [45.719999, 16.3418]
#     m = folium.Map(location=ivanic_grad_coords, zoom_start=16)

#     # Define common icon color for the pins (orange pin and black symbol)
#     pin_color = 'orange'
#     symbol_color = 'black'  # Set the icon (symbol) color to black

#     # Add glider markers
#     for _, row in glider_df.iterrows():
#         # Create popup content for glider data
#         popup_content = "<strong>Glider Data:</strong><br>"
#         for layer in selected_glider_layers:
#             popup_content += f"{layer}: {row[layer]}<br>"
#         popup_content += f"Altitude: {row['Alt']}<br>"
#         popup_content += f"Time: {row['time']}<br>"
        
#         # Use a custom icon for glider without shadow
#         folium.Marker(
#             location=[row['Lat'], row['Long']],
#             icon=folium.Icon(color=pin_color, icon='plane', prefix='fa', icon_color=symbol_color, shadow=False),
#             popup=popup_content
#         ).add_to(m)

#     # Add drone markers
#     for _, row in drone_df.iterrows():
#         # Create popup content for drone data
#         popup_content = "<strong>Drone Data:</strong><br>"
#         for layer in selected_drone_layers:
#             popup_content += f"{layer}: {row[layer]}<br>"
#         popup_content += f"Altitude: {row['Alt']}<br>"
#         popup_content += f"Timestamp: {row['Timestamp']}<br>"
        
#         # Use a custom icon for drone without shadow
#         folium.Marker(
#             location=[row['Lat'], row['Long']],
#             icon=folium.Icon(color=pin_color, icon='rocket', prefix='fa', icon_color=symbol_color, shadow=False),
#             popup=popup_content
#         ).add_to(m)

#     # Add heatmap for humidity data if the user wants to see it
#     if show_humidity_heatmap:
#         # Combine humidity data from both datasets
#         humidity_data = pd.concat([
#             glider_df[['Lat', 'Long', 'Hum']].rename(columns={'Hum': 'Humidity'}),
#             drone_df[['Lat', 'Long', 'Humidity']]
#         ]).dropna()
        
#         # Create heat data
#         heat_data = [[row['Lat'], row['Long'], row['Humidity']] for _, row in humidity_data.iterrows()]

#         # Modify HeatMap parameters for smoother effect
#         HeatMap(data=heat_data, radius=25, blur=15, max_zoom=1, 
#                 gradient={0.0: 'blue', 0.5: 'lime', 1.0: 'red'}).add_to(m)

#         # Add custom legend for the heatmap
#         legend_html = """
#         <div style="position: fixed; 
#                     bottom: 50px; left: 50px; width: 150px; height: 130px; 
#                     border:2px solid grey; z-index:9999; font-size:14px; 
#                     background-color: white; opacity: 0.8;">
#             <h4 style="text-align: center;">Humidity Legend</h4>
#             <i style="background: blue; width: 20px; height: 20px; display: inline-block;"></i> Low<br>
#             <i style="background: lime; width: 20px; height: 20px; display: inline-block;"></i> Moderate<br>
#             <i style="background: red; width: 20px; height: 20px; display: inline-block;"></i> High<br>
#         </div>
#         """
#         m.get_root().html.add_child(folium.Element(legend_html))

#     # Add combined heatmap for glider and drone temperature data if selected
#     if show_temp_heatmap:
#         # Combine temperature data from both datasets
#         temp_data = pd.concat([
#             glider_df[['Lat', 'Long', 'Temp']].rename(columns={'Temp': 'Temperature'}),
#             drone_df[['Lat', 'Long', 'Temperature']]
#         ]).dropna()
        
#         # Create heat data
#         heat_data_temp = [[row['Lat'], row['Long'], row['Temperature']] for _, row in temp_data.iterrows()]

#         # Add temperature heatmap
#         HeatMap(data=heat_data_temp, radius=25, blur=15, max_zoom=1, 
#                 gradient={0.0: 'blue', 0.5: 'yellow', 1.0: 'red'}).add_to(m)

#     # Add layer control
#     folium.LayerControl().add_to(m)
    
#     return m

# # Function to plot the correlation matrix
# def plot_correlation_matrix(df, selected_layers):
#     # Compute the correlation matrix
#     corr_matrix = df[selected_layers].corr()

#     # Create a heatmap plot using Seaborn
#     plt.figure(figsize=(10, 8))
#     sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', cbar=True)
#     plt.title('Correlation Matrix')

#     # Display the heatmap plot using Streamlit
#     st.pyplot(plt)

# # Streamlit app
# def main():
#     # Specify file paths directly
#     glider_file = '/Users/petra/Desktop/glider.csv'
#     drone_file = '/Users/petra/Desktop/drone.csv'

#     # Load data without uploading
#     glider_data, drone_data = load_data(glider_file, drone_file)
    
#     # Filter Glider Data by Time
#     st.sidebar.subheader("Select Time Range for Glider Data")
#     min_time = glider_data['time'].min()
#     max_time = glider_data['time'].max()

#     # Ensure that the time range is correctly recognized as datetime
#     if pd.isnull(min_time) or pd.isnull(max_time):
#         st.error("Glider time data is missing or invalid. Please check your data.")
#         return
    
#     selected_time_range = st.sidebar.slider(
#         "Select time range for Glider",
#         min_value=min_time.to_pydatetime(),  
#         max_value=max_time.to_pydatetime(),
#         value=(min_time.to_pydatetime(), max_time.to_pydatetime()),
#         format="YYYY-MM-DD HH:mm",
#         key="glider_time_slider"  # Unique key for Glider time range slider
#     )

#     # Filter glider data by selected time range
#     glider_data_filtered = glider_data[(glider_data['time'] >= selected_time_range[0]) & 
#                                         (glider_data['time'] <= selected_time_range[1])]

#     # Filter Drone Data by Time
#     st.sidebar.subheader("Select Time Range for Drone Data")
#     min_drone_time = drone_data['Timestamp'].min()
#     max_drone_time = drone_data['Timestamp'].max()

#     # Ensure that the time range is correctly recognized as datetime
#     if pd.isnull(min_drone_time) or pd.isnull(max_drone_time):
#         st.error("Drone time data is missing or invalid. Please check your data.")
#         return
    
#     selected_drone_time_range = st.sidebar.slider(
#         "Select time range for Drone",
#         min_value=min_drone_time.to_pydatetime(),  
#         max_value=max_drone_time.to_pydatetime(),
#         value=(min_drone_time.to_pydatetime(), max_drone_time.to_pydatetime()),
#         format="YYYY-MM-DD HH:mm",
#         key="drone_time_slider"  # Unique key for Drone time range slider
#     )

#     # Filter drone data by selected time range
#     drone_data_filtered = drone_data[(drone_data['Timestamp'] >= selected_drone_time_range[0]) & 
#                                       (drone_data['Timestamp'] <= selected_drone_time_range[1])]

#     # Create sidebar for selecting which layers to display
#     st.sidebar.subheader("Select Layers to Display")
#     glider_layers = ['P2_5', 'unknown', 'P10', 'UV', 'CO', 'Fire', 'H2', 'Temp', 'Hum']
#     drone_layers = ['Particles>0.3um', 'Particles>0.5um', 'Particles>1.0um', 
#                     'Particles>2.5um', 'Particles>5.0um', 'Particles>10.0um', 
#                     'PM1.0', 'PM2.5', 'PM10', 'Humidity', 'Temperature']

#     selected_glider_layers = st.sidebar.multiselect("Glider Layers", glider_layers, default=glider_layers)
#     selected_drone_layers = st.sidebar.multiselect("Drone Layers", drone_layers, default=drone_layers)

#     # Checkbox for displaying all glider markers
#     show_all_gliders = st.sidebar.checkbox("Show All Glider Markers", value=False)
#     # Checkbox for displaying all drone markers
#     show_all_drones = st.sidebar.checkbox("Show All Drone Markers", value=False)

#     # Allow user to choose whether to show heatmaps
#     st.sidebar.subheader("Heatmap Options")
#     show_humidity_heatmap = st.sidebar.checkbox("Show Humidity Heatmap", value=False)
#     show_temp_heatmap = st.sidebar.checkbox("Show Temperature Heatmap", value=False)

#     # Determine whether to use filtered data or show all markers based on checkboxes
#     if show_all_gliders:
#         glider_data_to_use = glider_data  # Use all glider data
#     else:
#         glider_data_to_use = glider_data_filtered  # Use filtered data

#     if show_all_drones:
#         drone_data_to_use = drone_data  # Use all drone data
#     else:
#         drone_data_to_use = drone_data_filtered  # Use filtered data

#     # Create the map with the selected data
#     map_ = create_map(glider_data_to_use, drone_data_to_use, selected_glider_layers, selected_drone_layers, show_humidity_heatmap, show_temp_heatmap)

#     # Display the map in the Streamlit app
#     st.subheader("Map")
#     st_folium(map_, width=700, height=500)

#     # Create correlation matrix if selected
#     if st.sidebar.button("Show Correlation Matrix"):
#         # Ensure dataframes are not empty
#         if not glider_data_filtered.empty:
#             plot_correlation_matrix(glider_data_filtered, selected_glider_layers)
#         else:
#             st.warning("No glider data available for the selected time range.")

#         if not drone_data_filtered.empty:
#             plot_correlation_matrix(drone_data_filtered, selected_drone_layers)
#         else:
#             st.warning("No drone data available for the selected time range.")

# # Run the app
# if __name__ == "__main__":
#     main()



# import pandas as pd
# import folium
# from folium.plugins import HeatMap, MarkerCluster
# import streamlit as st
# from streamlit_folium import st_folium
# import seaborn as sns
# import matplotlib.pyplot as plt
# import random

# # Configure the page layout to be wide
# st.set_page_config(layout="wide")

# # Function to load CSV data
# @st.cache_data
# def load_data(glider_file, drone_file):
#     # Load glider data
#     glider_df = pd.read_csv(glider_file)
#     glider_df.columns = ['Unnamed: 0', 'time', 'P2_5', 'unknown', 'P10', 'UV', 'CO', 'Fire', 'H2', 'Temp', 'Hum', 'Lat', 'Long', 'Alt']
    
#     # Convert 'time' column to datetime
#     glider_df['time'] = pd.to_datetime(glider_df['time'], errors='coerce')
    
#     # Load drone data
#     drone_df = pd.read_csv(drone_file, delimiter=';')
#     drone_df.columns = ['Unnamed: 0', 'Timestamp', 'Millis', 'Particles>0.3um', 'Particles>0.5um', 
#                         'Particles>1.0um', 'Particles>2.5um', 'Particles>5.0um', 
#                         'Particles>10.0um', 'PM1.0', 'PM2.5', 'PM10', 'Humidity', 
#                         'Temperature', 'flight_iteration', 'Lat', 'Long', 'Alt']
    
#     # Convert 'Timestamp' to datetime
#     drone_df['Timestamp'] = pd.to_datetime(drone_df['Timestamp'], errors='coerce')
    
#     return glider_df, drone_df

# # Function to create Folium map
# @st.cache_data  # Cache the map creation to avoid re-rendering
# def create_map(glider_df, drone_df, selected_glider_layers, selected_drone_layers, show_humidity_heatmap):
#     # Center the map on Ivanic Grad [45.719999, 16.3418] and set zoom level to 16
#     ivanic_grad_coords = [45.719999, 16.3418]
#     m = folium.Map(location=ivanic_grad_coords, zoom_start=16)

#     # Define common icon color
#     icon_color = 'black'  # Set icon color to black

#     # Add glider markers
#     for _, row in glider_df.iterrows():
#         # Create popup content for glider data
#         popup_content = "<strong>Glider Data:</strong><br>"
#         for layer in selected_glider_layers:
#             popup_content += f"{layer}: {row[layer]}<br>"
#         popup_content += f"Altitude: {row['Alt']}<br>"
#         popup_content += f"Time: {row['time']}<br>"
        
#         # Use a small custom icon for glider
#         folium.Marker(
#             location=[row['Lat'], row['Long']],
#             icon=folium.Icon(color=icon_color, icon='plane', prefix='fa', icon_color='white', icon_size=(10, 10)),
#             popup=popup_content
#         ).add_to(m)

#     # Add drone markers
#     for _, row in drone_df.iterrows():
#         # Create popup content for drone data
#         popup_content = "<strong>Drone Data:</strong><br>"
#         for layer in selected_drone_layers:
#             popup_content += f"{layer}: {row[layer]}<br>"
#         popup_content += f"Altitude: {row['Alt']}<br>"
#         popup_content += f"Timestamp: {row['Timestamp']}<br>"
        
#         # Use a small custom icon for drone
#         folium.Marker(
#             location=[row['Lat'], row['Long']],
#             icon=folium.Icon(color=icon_color, icon='rocket', prefix='fa', icon_color='white', icon_size=(10, 10)),
#             popup=popup_content
#         ).add_to(m)

#     # Add heatmap for humidity data if the user wants to see it
#     if show_humidity_heatmap:
#         # Combine humidity data from both datasets
#         humidity_data = pd.concat([
#             glider_df[['Lat', 'Long', 'Hum']].rename(columns={'Hum': 'Humidity'}),
#             drone_df[['Lat', 'Long', 'Humidity']]
#         ]).dropna()
        
#         # Create heat data
#         heat_data = [[row['Lat'], row['Long'], row['Humidity']] for _, row in humidity_data.iterrows()]

#         # Modify HeatMap parameters for smoother effect
#         HeatMap(data=heat_data, radius=25, blur=15, max_zoom=1, 
#                 gradient={0.0: 'blue', 0.5: 'lime', 1.0: 'red'}).add_to(m)

#         # Add custom legend for the heatmap
#         legend_html = """
#         <div style="position: fixed; 
#                     bottom: 50px; left: 50px; width: 150px; height: 130px; 
#                     border:2px solid grey; z-index:9999; font-size:14px; 
#                     background-color: white; opacity: 0.8;">
#             <h4 style="text-align: center;">Humidity Legend</h4>
#             <i style="background: blue; width: 20px; height: 20px; display: inline-block;"></i> Low<br>
#             <i style="background: lime; width: 20px; height: 20px; display: inline-block;"></i> Moderate<br>
#             <i style="background: red; width: 20px; height: 20px; display: inline-block;"></i> High<br>
#         </div>
#         """
#         m.get_root().html.add_child(folium.Element(legend_html))

#     # Add layer control
#     folium.LayerControl().add_to(m)
    
#     return m

# # Function to plot the correlation matrix
# def plot_correlation_matrix(df, selected_layers):
#     # Compute the correlation matrix
#     corr_matrix = df[selected_layers].corr()

#     # Create a heatmap plot using Seaborn
#     plt.figure(figsize=(10, 8))
#     sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', cbar=True)
#     plt.title('Correlation Matrix')

#     # Display the heatmap plot using Streamlit
#     st.pyplot(plt)

# # Streamlit app
# def main():
#     # Specify file paths directly
#     glider_file = '/Users/petra/Desktop/glider.csv'
#     drone_file = '/Users/petra/Desktop/drone.csv'

#     # Load data without uploading
#     glider_data, drone_data = load_data(glider_file, drone_file)
    
#     # Filter Glider Data by Time
#     st.sidebar.subheader("Select Time Range for Glider Data")
#     min_time = glider_data['time'].min()
#     max_time = glider_data['time'].max()

#     # Ensure that the time range is correctly recognized as datetime
#     if pd.isnull(min_time) or pd.isnull(max_time):
#         st.error("Glider time data is missing or invalid. Please check your data.")
#         return
    
#     selected_time_range = st.sidebar.slider(
#         "Select time range for Glider",
#         min_value=min_time.to_pydatetime(),  
#         max_value=max_time.to_pydatetime(),
#         value=(min_time.to_pydatetime(), max_time.to_pydatetime()),
#         format="YYYY-MM-DD HH:mm"
#     )

#     # Filter glider data by selected time range
#     glider_data_filtered = glider_data[(glider_data['time'] >= selected_time_range[0]) & 
#                                         (glider_data['time'] <= selected_time_range[1])]

#     # Filter Drone Data by Time
#     st.sidebar.subheader("Select Time Range for Drone Data")
#     min_drone_time = drone_data['Timestamp'].min()
#     max_drone_time = drone_data['Timestamp'].max()

#     # Ensure that the time range is correctly recognized as datetime
#     if pd.isnull(min_drone_time) or pd.isnull(max_drone_time):
#         st.error("Drone time data is missing or invalid. Please check your data.")
#         return
    
#     selected_drone_time_range = st.sidebar.slider(
#         "Select time range for Drone",
#         min_value=min_drone_time.to_pydatetime(),  
#         max_value=max_drone_time.to_pydatetime(),
#         value=(min_drone_time.to_pydatetime(), max_drone_time.to_pydatetime()),
#         format="YYYY-MM-DD HH:mm"
#     )

#     # Filter drone data by selected time range
#     drone_data_filtered = drone_data[(drone_data['Timestamp'] >= selected_drone_time_range[0]) & 
#                                      (drone_data['Timestamp'] <= selected_drone_time_range[1])]

#     # Create checkboxes for glider data columns (excluding 'time', 'Lat', and 'Long')
#     st.sidebar.subheader("Select Glider Data Layers to Display")
#     glider_columns = ['P2_5', 'P10', 'UV', 'CO', 'Fire', 'H2', 'Temp', 'Hum', 'Alt']
#     selected_glider_layers = [col for col in glider_columns if st.sidebar.checkbox(f"Glider - {col}", value=False)]

#     # Create checkboxes for drone data columns (excluding 'Timestamp', 'Millis', 'Lat', and 'Long')
#     st.sidebar.subheader("Select Drone Data Layers to Display")
#     drone_columns = ['Particles>0.3um', 'Particles>0.5um', 'Particles>1.0um', 
#                      'Particles>2.5um', 'Particles>5.0um', 'Particles>10.0um', 
#                      'PM1.0', 'PM2.5', 'PM10', 'Humidity', 'Temperature', 'flight_iteration', 'Alt']
#     selected_drone_layers = [col for col in drone_columns if st.sidebar.checkbox(f"Drone - {col}", value=False)]

#     # Add dropdown for flight iteration selection
#     st.sidebar.subheader("Select Flight Iteration")
#     flight_iterations = drone_data['flight_iteration'].unique()
#     selected_flight_iteration = st.sidebar.selectbox("Flight Iteration", options=["All"] + flight_iterations.tolist())

#     # Filter drone data based on selected flight iteration
#     if selected_flight_iteration != "All":
#         drone_data_filtered = drone_data_filtered[drone_data_filtered['flight_iteration'] == selected_flight_iteration]

#     # Option to display humidity heatmap
#     show_humidity_heatmap = st.sidebar.checkbox("Show Humidity Heatmap", value=False)

#     # Create the map with the selected filters and options
#     map_display = create_map(glider_data_filtered, drone_data_filtered, selected_glider_layers, selected_drone_layers, show_humidity_heatmap)

#     # Display the map in the Streamlit app
#     st_folium(map_display, width=2000, height=800)  # Set width and height of the map

#     # Display correlation matrix based on selected layers
#     st.subheader("Correlation Matrix")
#     if selected_glider_layers or selected_drone_layers:
#         combined_data = pd.concat([glider_data_filtered[selected_glider_layers], drone_data_filtered[selected_drone_layers]], axis=1)
#         plot_correlation_matrix(combined_data, selected_glider_layers + selected_drone_layers)
#     else:
#         st.write("Please select some data layers from the sidebar to display the correlation matrix.")

# if __name__ == "__main__":
#     main()


# import pandas as pd
# import folium
# from folium.plugins import HeatMap, MarkerCluster
# import streamlit as st
# from streamlit_folium import st_folium
# import seaborn as sns
# import matplotlib.pyplot as plt
# import random

# # Configure the page layout to be wide
# st.set_page_config(layout="wide")

# # Function to load CSV data
# @st.cache_data
# def load_data(glider_file, drone_file):
#     # Load glider data
#     glider_df = pd.read_csv(glider_file)
#     glider_df.columns = ['Unnamed: 0', 'time', 'P2_5', 'unknown', 'P10', 'UV', 'CO', 'Fire', 'H2', 'Temp', 'Hum', 'Lat', 'Long', 'Alt']
    
#     # Convert 'time' column to datetime
#     glider_df['time'] = pd.to_datetime(glider_df['time'], errors='coerce')
    
#     # Load drone data
#     drone_df = pd.read_csv(drone_file, delimiter=';')
#     drone_df.columns = ['Unnamed: 0', 'Timestamp', 'Millis', 'Particles>0.3um', 'Particles>0.5um', 
#                         'Particles>1.0um', 'Particles>2.5um', 'Particles>5.0um', 
#                         'Particles>10.0um', 'PM1.0', 'PM2.5', 'PM10', 'Humidity', 
#                         'Temperature', 'flight_iteration', 'Lat', 'Long', 'Alt']
    
#     # Convert 'Timestamp' to datetime
#     drone_df['Timestamp'] = pd.to_datetime(drone_df['Timestamp'], errors='coerce')
    
#     return glider_df, drone_df

# # Function to add dynamic jitter to coordinates based on density
# def jitter_coordinates(lat, long, density_count, base_jitter=0.00005, density_factor=0.00005):
#     # Dynamic jitter strength based on density
#     jitter_strength = base_jitter + (density_factor * density_count)
#     return lat + random.uniform(-jitter_strength, jitter_strength), long + random.uniform(-jitter_strength, jitter_strength)

# # Function to create Folium map
# @st.cache_data  # Cache the map creation to avoid re-rendering
# def create_map(glider_df, drone_df, selected_glider_layers, selected_drone_layers, show_humidity_heatmap):
#     # Center the map on Ivanic Grad [45.719999, 16.3418] and set zoom level to 16
#     ivanic_grad_coords = [45.719999, 16.3418]
#     m = folium.Map(location=ivanic_grad_coords, zoom_start=16)

#     # Initialize Marker Cluster
#     marker_cluster = MarkerCluster().add_to(m)

#     # Define common icon color
#     icon_color = 'black'  # Set icon color to black

#     # Add glider data points if layers are selected
#     glider_density = glider_df[['Lat', 'Long']].value_counts().reset_index(name='count')
    
#     for _, row in glider_df.iterrows():
#         density_count = glider_density.loc[
#             (glider_density['Lat'] == row['Lat']) & (glider_density['Long'] == row['Long']), 'count'
#         ].values[0]
        
#         # Create popup content for glider data, including altitude
#         popup_content = "<strong>Glider Data:</strong><br>"
#         for layer in selected_glider_layers:
#             popup_content += f"{layer}: {row[layer]}<br>"
#         popup_content += f"Altitude: {row['Alt']}<br>"
#         popup_content += f"Time: {row['time']}<br>"
        
#         # Apply dynamic jitter to avoid overlapping markers
#         lat, long = jitter_coordinates(row['Lat'], row['Long'], density_count)

#         # Use custom smaller icon for glider
#         folium.Marker(
#             location=[lat, long],
#             icon=folium.Icon(color=icon_color, icon='plane', prefix='fa', icon_color='white', icon_size=(10, 10)),
#             popup=popup_content
#         ).add_to(marker_cluster)  # Add to the cluster

#     # Add drone data points if layers are selected
#     drone_density = drone_df[['Lat', 'Long']].value_counts().reset_index(name='count')

#     for _, row in drone_df.iterrows():
#         density_count = drone_density.loc[
#             (drone_density['Lat'] == row['Lat']) & (drone_density['Long'] == row['Long']), 'count'
#         ].values[0]
        
#         # Create popup content for drone data, including altitude
#         popup_content = "<strong>Drone Data:</strong><br>"
#         for layer in selected_drone_layers:
#             popup_content += f"{layer}: {row[layer]}<br>"
#         popup_content += f"Altitude: {row['Alt']}<br>"
#         popup_content += f"Timestamp: {row['Timestamp']}<br>"
        
#         # Apply dynamic jitter to avoid overlapping markers
#         lat, long = jitter_coordinates(row['Lat'], row['Long'], density_count)

#         # Use custom smaller icon for drone
#         folium.Marker(
#             location=[lat, long],
#             icon=folium.Icon(color=icon_color, icon='rocket', prefix='fa', icon_color='white', icon_size=(10, 10)),
#             popup=popup_content
#         ).add_to(marker_cluster)  # Add to the cluster

#     # Add heatmap for humidity data if the user wants to see it
#     if show_humidity_heatmap:
#         # Combine humidity data from both datasets
#         humidity_data = pd.concat([
#             glider_df[['Lat', 'Long', 'Hum']].rename(columns={'Hum': 'Humidity'}),
#             drone_df[['Lat', 'Long', 'Humidity']]
#         ]).dropna()
        
#         # Create heat data
#         heat_data = [[row['Lat'], row['Long'], row['Humidity']] for _, row in humidity_data.iterrows()]

#         # Modify HeatMap parameters for smoother effect
#         HeatMap(data=heat_data, radius=25, blur=15, max_zoom=1, 
#                 gradient={0.0: 'blue', 0.5: 'lime', 1.0: 'red'}).add_to(m)

#         # Add custom legend for the heatmap
#         legend_html = """
#         <div style="position: fixed; 
#                     bottom: 50px; left: 50px; width: 150px; height: 130px; 
#                     border:2px solid grey; z-index:9999; font-size:14px; 
#                     background-color: white; opacity: 0.8;">
#             <h4 style="text-align: center;">Humidity Legend</h4>
#             <i style="background: blue; width: 20px; height: 20px; display: inline-block;"></i> Low<br>
#             <i style="background: lime; width: 20px; height: 20px; display: inline-block;"></i> Moderate<br>
#             <i style="background: red; width: 20px; height: 20px; display: inline-block;"></i> High<br>
#         </div>
#         """
#         m.get_root().html.add_child(folium.Element(legend_html))

#     # Add layer control
#     folium.LayerControl().add_to(m)
    
#     return m

# # Function to plot the correlation matrix
# def plot_correlation_matrix(df, selected_layers):
#     # Compute the correlation matrix
#     corr_matrix = df[selected_layers].corr()

#     # Create a heatmap plot using Seaborn
#     plt.figure(figsize=(10, 8))
#     sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', cbar=True)
#     plt.title('Correlation Matrix')

#     # Display the heatmap plot using Streamlit
#     st.pyplot(plt)

# # Streamlit app
# def main():
#     # Specify file paths directly
#     glider_file = '/Users/petra/Desktop/glider.csv'
#     drone_file = '/Users/petra/Desktop/drone.csv'

#     # Load data without uploading
#     glider_data, drone_data = load_data(glider_file, drone_file)
    
#     # Filter Glider Data by Time
#     st.sidebar.subheader("Select Time Range for Glider Data")
#     min_time = glider_data['time'].min()
#     max_time = glider_data['time'].max()

#     # Ensure that the time range is correctly recognized as datetime
#     if pd.isnull(min_time) or pd.isnull(max_time):
#         st.error("Glider time data is missing or invalid. Please check your data.")
#         return
    
#     selected_time_range = st.sidebar.slider(
#         "Select time range for Glider",
#         min_value=min_time.to_pydatetime(),  
#         max_value=max_time.to_pydatetime(),
#         value=(min_time.to_pydatetime(), max_time.to_pydatetime()),
#         format="YYYY-MM-DD HH:mm"
#     )

#     # Filter glider data by selected time range
#     glider_data_filtered = glider_data[(glider_data['time'] >= selected_time_range[0]) & 
#                                         (glider_data['time'] <= selected_time_range[1])]

#     # Filter Drone Data by Time
#     st.sidebar.subheader("Select Time Range for Drone Data")
#     min_drone_time = drone_data['Timestamp'].min()
#     max_drone_time = drone_data['Timestamp'].max()

#     # Ensure that the time range is correctly recognized as datetime
#     if pd.isnull(min_drone_time) or pd.isnull(max_drone_time):
#         st.error("Drone time data is missing or invalid. Please check your data.")
#         return
    
#     selected_drone_time_range = st.sidebar.slider(
#         "Select time range for Drone",
#         min_value=min_drone_time.to_pydatetime(),  
#         max_value=max_drone_time.to_pydatetime(),
#         value=(min_drone_time.to_pydatetime(), max_drone_time.to_pydatetime()),
#         format="YYYY-MM-DD HH:mm"
#     )

#     # Filter drone data by selected time range
#     drone_data_filtered = drone_data[(drone_data['Timestamp'] >= selected_drone_time_range[0]) & 
#                                      (drone_data['Timestamp'] <= selected_drone_time_range[1])]

#     # Create checkboxes for glider data columns (excluding 'time', 'Lat', and 'Long')
#     st.sidebar.subheader("Select Glider Data Layers to Display")
#     glider_columns = ['P2_5', 'P10', 'UV', 'CO', 'Fire', 'H2', 'Temp', 'Hum', 'Alt']
#     selected_glider_layers = [col for col in glider_columns if st.sidebar.checkbox(f"Glider - {col}", value=False)]

#     # Create checkboxes for drone data columns (excluding 'Timestamp', 'Millis', 'Lat', and 'Long')
#     st.sidebar.subheader("Select Drone Data Layers to Display")
#     drone_columns = ['Particles>0.3um', 'Particles>0.5um', 'Particles>1.0um', 
#                      'Particles>2.5um', 'Particles>5.0um', 'Particles>10.0um', 
#                      'PM1.0', 'PM2.5', 'PM10', 'Humidity', 'Temperature', 'flight_iteration', 'Alt']
#     selected_drone_layers = [col for col in drone_columns if st.sidebar.checkbox(f"Drone - {col}", value=False)]

#     # Add dropdown for flight iteration selection
#     st.sidebar.subheader("Select Flight Iteration")
#     flight_iterations = drone_data['flight_iteration'].unique()
#     selected_flight_iteration = st.sidebar.selectbox("Flight Iteration", options=["All"] + flight_iterations.tolist())

#     # Filter drone data based on selected flight iteration
#     if selected_flight_iteration != "All":
#         drone_data_filtered = drone_data_filtered[drone_data_filtered['flight_iteration'] == selected_flight_iteration]

#     # Option to display humidity heatmap
#     show_humidity_heatmap = st.sidebar.checkbox("Show Humidity Heatmap", value=False)

#     # Create the map with the selected filters and options
#     map_display = create_map(glider_data_filtered, drone_data_filtered, selected_glider_layers, selected_drone_layers, show_humidity_heatmap)

#     # Display the map in the Streamlit app
#     st_folium(map_display, width=2000, height=800)  # Set width and height of the map

#     # Display correlation matrix based on selected layers
#     st.subheader("Correlation Matrix")
#     if selected_glider_layers or selected_drone_layers:
#         combined_data = pd.concat([glider_data_filtered[selected_glider_layers], drone_data_filtered[selected_drone_layers]], axis=1)
#         plot_correlation_matrix(combined_data, selected_glider_layers + selected_drone_layers)
#     else:
#         st.write("Please select some data layers from the sidebar to display the correlation matrix.")

# if __name__ == "__main__":
#     main()





# import pandas as pd
# import folium
# from folium.plugins import HeatMap
# import streamlit as st
# from streamlit_folium import st_folium

# # Configure the page layout to be wide
# st.set_page_config(layout="wide")

# # Function to load CSV data
# def load_data(glider_file, drone_file):
#     # Load glider data
#     glider_df = pd.read_csv(glider_file)
#     glider_df.columns = ['Unnamed: 0', 'time', 'P2_5', 'unknown', 'P10', 'UV', 'CO', 'Fire', 'H2', 'Temp', 'Hum', 'Lat', 'Long', 'Alt']
    
#     # Convert 'time' column to datetime
#     glider_df['time'] = pd.to_datetime(glider_df['time'], errors='coerce')
    
#     # Load drone data
#     drone_df = pd.read_csv(drone_file, delimiter=';')
#     drone_df.columns = ['Unnamed: 0', 'Timestamp', 'Millis', 'Particles>0.3um', 'Particles>0.5um', 
#                         'Particles>1.0um', 'Particles>2.5um', 'Particles>5.0um', 
#                         'Particles>10.0um', 'PM1.0', 'PM2.5', 'PM10', 'Humidity', 
#                         'Temperature', 'flight_iteration', 'Lat', 'Long', 'Alt']
    
#     # Convert 'Timestamp' to datetime
#     drone_df['Timestamp'] = pd.to_datetime(drone_df['Timestamp'], errors='coerce')
    
#     return glider_df, drone_df

# # Function to create Folium map
# def create_map(glider_df, drone_df, selected_glider_layers, selected_drone_layers, show_humidity_heatmap):
#     # Center the map on Ivanic Grad [45.719999, 16.3418] and set zoom level to 16
#     ivanic_grad_coords = [45.719999, 16.3418]
#     m = folium.Map(location=ivanic_grad_coords, zoom_start=16)

#     # Define common icon color
#     icon_color = 'black'  # Set icon color to black

#     # Add glider data points if layers are selected
#     for _, row in glider_df.iterrows():
#         # Create popup content for glider data
#         popup_content = "<strong>Glider Data:</strong><br>"
#         for layer in selected_glider_layers:
#             popup_content += f"{layer}: {row[layer]}<br>"
#         popup_content += f"Time: {row['time']}<br>"
        
#         # Use custom smaller icon for glider
#         folium.Marker(
#             location=[row['Lat'], row['Long']],
#             icon=folium.Icon(color=icon_color, icon='plane', prefix='fa', icon_color='white', scale=0.),  # Smaller icon for glider
#             popup=popup_content
#         ).add_to(m)

#     # Add drone data points if layers are selected
#     for _, row in drone_df.iterrows():
#         # Create popup content for drone data
#         popup_content = "<strong>Drone Data:</strong><br>"
#         for layer in selected_drone_layers:
#             popup_content += f"{layer}: {row[layer]}<br>"
#         popup_content += f"Timestamp: {row['Timestamp']}<br>"
        
#         # Use custom smaller icon for drone
#         folium.Marker(
#             location=[row['Lat'], row['Long']],
#             icon=folium.Icon(color=icon_color, icon='rocket', prefix='fa', icon_color='white', scale=0.5),  # Smaller icon for drone
#             popup=popup_content
#         ).add_to(m)

#     # Add heatmap for humidity data if the user wants to see it
#     if show_humidity_heatmap:
#         # Combine humidity data from both datasets
#         humidity_data = pd.concat([
#             glider_df[['Lat', 'Long', 'Hum']].rename(columns={'Hum': 'Humidity'}),
#             drone_df[['Lat', 'Long', 'Humidity']]
#         ]).dropna()
        
#         # Create heat data
#         heat_data = [[row['Lat'], row['Long'], row['Humidity']] for _, row in humidity_data.iterrows()]

#         # Modify HeatMap parameters for smoother effect
#         HeatMap(data=heat_data, radius=25, blur=15, max_zoom=1, 
#                 gradient={0.0: 'blue', 0.5: 'lime', 1.0: 'red'}).add_to(m)

#         # Add custom legend for the heatmap
#         legend_html = """
#         <div style="position: fixed; 
#                     bottom: 50px; left: 50px; width: 150px; height: 130px; 
#                     border:2px solid grey; z-index:9999; font-size:14px; 
#                     background-color: white; opacity: 0.8;">
#             <h4 style="text-align: center;">Humidity Legend</h4>
#             <i style="background: blue; width: 20px; height: 20px; display: inline-block;"></i> Low<br>
#             <i style="background: lime; width: 20px; height: 20px; display: inline-block;"></i> Moderate<br>
#             <i style="background: red; width: 20px; height: 20px; display: inline-block;"></i> High<br>
#         </div>
#         """
#         m.get_root().html.add_child(folium.Element(legend_html))

#     # Add layer control
#     folium.LayerControl().add_to(m)
    
#     return m

# # Streamlit app
# def main():
#     # Specify file paths directly
#     glider_file = '/Users/petra/Desktop/glider.csv'
#     drone_file = '/Users/petra/Desktop/drone.csv'

#     # Load data without uploading
#     glider_data, drone_data = load_data(glider_file, drone_file)
    
#     # Filter Glider Data by Time
#     st.sidebar.subheader("Select Time Range for Glider Data")
#     min_time = glider_data['time'].min()
#     max_time = glider_data['time'].max()

#     # Ensure that the time range is correctly recognized as datetime
#     if pd.isnull(min_time) or pd.isnull(max_time):
#         st.error("Glider time data is missing or invalid. Please check your data.")
#         return
    
#     selected_time_range = st.sidebar.slider(
#         "Select time range for Glider",
#         min_value=min_time.to_pydatetime(),  
#         max_value=max_time.to_pydatetime(),
#         value=(min_time.to_pydatetime(), max_time.to_pydatetime()),
#         format="YYYY-MM-DD HH:mm"
#     )

#     # Filter glider data by selected time range
#     glider_data_filtered = glider_data[(glider_data['time'] >= selected_time_range[0]) & 
#                                        (glider_data['time'] <= selected_time_range[1])]

#     # Filter Drone Data by Timestamp
#     st.sidebar.subheader("Select Time Range for Drone Data")
#     min_drone_time = drone_data['Timestamp'].min()
#     max_drone_time = drone_data['Timestamp'].max()

#     # Ensure that the drone timestamp range is correctly recognized as datetime
#     if pd.isnull(min_drone_time) or pd.isnull(max_drone_time):
#         st.error("Drone timestamp data is missing or invalid. Please check your data.")
#         return
    
#     selected_drone_time_range = st.sidebar.slider(
#         "Select time range for Drone",
#         min_value=min_drone_time.to_pydatetime(),  
#         max_value=max_drone_time.to_pydatetime(),
#         value=(min_drone_time.to_pydatetime(), max_drone_time.to_pydatetime()),
#         format="YYYY-MM-DD HH:mm"
#     )

#     # Filter drone data by selected timestamp range
#     drone_data_filtered = drone_data[(drone_data['Timestamp'] >= selected_drone_time_range[0]) & 
#                                      (drone_data['Timestamp'] <= selected_drone_time_range[1])]

#     # Create checkboxes for glider data columns (excluding 'unknown', 'Lat', and 'Long')
#     st.sidebar.subheader("Select Glider Data Layers to Display")
#     glider_columns = ['P2_5', 'P10', 'UV', 'CO', 'Fire', 'H2', 'Temp', 'Hum', 'Alt']
#     selected_glider_layers = [col for col in glider_columns if st.sidebar.checkbox(f"Glider - {col}", value=False)]

#     # Create checkboxes for drone data columns (excluding 'Timestamp', 'Millis', 'Lat', and 'Long')
#     st.sidebar.subheader("Select Drone Data Layers to Display")
#     drone_columns = ['Particles>0.3um', 'Particles>0.5um', 'Particles>1.0um', 
#                      'Particles>2.5um', 'Particles>5.0um', 'Particles>10.0um', 
#                      'PM1.0', 'PM2.5', 'PM10', 'Humidity', 'Temperature', 'flight_iteration', 'Alt']
#     selected_drone_layers = [col for col in drone_columns if st.sidebar.checkbox(f"Drone - {col}", value=False)]

#     # Add dropdown for flight iteration selection
#     st.sidebar.subheader("Select Flight Iteration")
#     flight_iterations = drone_data['flight_iteration'].unique()
#     selected_flight_iteration = st.sidebar.selectbox("Flight Iteration", options=["All"] + flight_iterations.tolist())

#     # Filter drone data based on selected flight iteration
#     if selected_flight_iteration != "All":
#         drone_data_filtered = drone_data_filtered[drone_data_filtered['flight_iteration'] == selected_flight_iteration]

#     # Option to display humidity heatmap
#     show_humidity_heatmap = st.sidebar.checkbox("Show Humidity Heatmap", value=False)

#     # Create the map with the selected filters and options
#     map_display = create_map(glider_data_filtered, drone_data_filtered, selected_glider_layers, selected_drone_layers, show_humidity_heatmap)

#     # Display the map in the Streamlit app
#     st_folium(map_display, width=2000, height=800)  # Set width and height of the map

# if __name__ == "__main__":
#     main()






# import pandas as pd
# import folium
# import streamlit as st
# from folium.plugins import MarkerCluster

# # Function to load CSV data
# def load_data(glider_file, drone_file):
#     # Load glider data
#     glider_df = pd.read_csv(glider_file)
#     glider_df.columns = ['Unnamed: 0', 'time', 'P2_5', 'unknown', 'P10', 'UV', 'CO', 'Fire', 'H2', 'Temp', 'Hum', 'Lat', 'Long', 'Alt']

#     # Load drone data
#     drone_df = pd.read_csv(drone_file, delimiter=';')
#     drone_df.columns = ['Unnamed: 0', 'Timestamp', 'Millis', 'Particles>0.3um', 'Particles>0.5um', 
#                         'Particles>1.0um', 'Particles>2.5um', 'Particles>5.0um', 
#                         'Particles>10.0um', 'PM1.0', 'PM2.5', 'PM10', 'Humidity', 
#                         'Temperature', 'flight_iteration', 'Lat', 'Long', 'Alt']
    
#     return glider_df, drone_df

# # Function to create Folium map
# def create_map(glider_df, drone_df, selected_glider_columns, selected_drone_columns):
#     # Create base map centered on average lat/long of both datasets
#     map_center = [(glider_df['Lat'].mean() + drone_df['Lat'].mean()) / 2, 
#                   (glider_df['Long'].mean() + drone_df['Long'].mean()) / 2]
    
#     m = folium.Map(location=map_center, zoom_start=10)

#     # Create marker clusters for better visualization
#     glider_cluster = MarkerCluster(name="Glider Data").add_to(m)
#     for i, row in glider_df.iterrows():
#         # Create a popup with selected glider data columns
#         popup_content = "<strong>Glider Data</strong><br>"
#         for column in selected_glider_columns:
#             popup_content += f"{column}: {row[column]}<br>"
#         folium.Marker(
#             location=[row['Lat'], row['Long']],
#             popup=popup_content,
#             icon=folium.Icon(color='blue')
#         ).add_to(glider_cluster)

#     drone_cluster = MarkerCluster(name="Drone Data").add_to(m)
#     for i, row in drone_df.iterrows():
#         # Create a popup with selected drone data columns
#         popup_content = "<strong>Drone Data</strong><br>"
#         for column in selected_drone_columns:
#             popup_content += f"{column}: {row[column]}<br>"
#         folium.Marker(
#             location=[row['Lat'], row['Long']],
#             popup=popup_content,
#             icon=folium.Icon(color='red')
#         ).add_to(drone_cluster)

#     # Add layer control
#     folium.LayerControl().add_to(m)
    
#     return m

# # Streamlit app
# def main():
#     st.title("Glider and Drone Data Visualization")

#     # Specify file paths directly
#     glider_file = '/Users/petra/Desktop/glider.csv'
#     drone_file = '/Users/petra/Desktop/drone.csv'

#     # Load data without uploading
#     glider_data, drone_data = load_data(glider_file, drone_file)
    
#     # Create checkboxes for glider data columns
#     st.subheader("Select Glider Data Columns to Display")
#     glider_columns = ['time', 'P2_5', 'unknown', 'P10', 'UV', 'CO', 'Fire', 'H2', 'Temp', 'Hum', 'Lat', 'Long', 'Alt']
#     selected_glider_columns = st.multiselect("Choose columns:", glider_columns, default=['time', 'P2_5', 'Temp', 'Hum'])

#     # Create checkboxes for drone data columns
#     st.subheader("Select Drone Data Columns to Display")
#     drone_columns = ['Timestamp', 'Millis', 'Particles>0.3um', 'Particles>0.5um', 'Particles>1.0um', 
#                      'Particles>2.5um', 'Particles>5.0um', 'Particles>10.0um', 'PM1.0', 'PM2.5', 'PM10', 
#                      'Humidity', 'Temperature', 'flight_iteration', 'Lat', 'Long', 'Alt']
#     selected_drone_columns = st.multiselect("Choose columns:", drone_columns, default=['Timestamp', 'PM2.5', 'Temperature'])

#     # Create and display map
#     folium_map = create_map(glider_data, drone_data, selected_glider_columns, selected_drone_columns)
    
#     # Save the map to an HTML file and display it
#     folium_map.save("map.html")
#     st.components.v1.html(open("map.html", "r").read(), width=800, height=600, scrolling=True)

# if __name__ == "__main__":
#     main()


# import pandas as pd
# import folium
# import streamlit as st
# from folium.plugins import MarkerCluster

# # Function to load CSV data
# def load_data(glider_file, drone_file):
#     # Load glider data
#     glider_df = pd.read_csv(glider_file)
#     glider_df.columns = ['Unnamed: 0', 'time', 'P2_5', 'unknown', 'P10', 'UV', 'CO', 'Fire', 'H2', 'Temp', 'Hum', 'Lat', 'Long', 'Alt']

#     # Load drone data
#     drone_df = pd.read_csv(drone_file, delimiter=';')
#     drone_df.columns = ['Unnamed: 0', 'Timestamp', 'Millis', 'Particles>0.3um', 'Particles>0.5um', 
#                         'Particles>1.0um', 'Particles>2.5um', 'Particles>5.0um', 
#                         'Particles>10.0um', 'PM1.0', 'PM2.5', 'PM10', 'Humidity', 
#                         'Temperature', 'flight_iteration', 'Lat', 'Long', 'Alt']
    
#     return glider_df, drone_df

# # Function to create Folium map
# def create_map(glider_df, drone_df, show_glider, show_drone):
#     # Create base map centered on average lat/long of both datasets
#     map_center = [(glider_df['Lat'].mean() + drone_df['Lat'].mean()) / 2, 
#                   (glider_df['Long'].mean() + drone_df['Long'].mean()) / 2]
    
#     m = folium.Map(location=map_center, zoom_start=10)

#     # Create marker clusters for better visualization
#     if show_glider:
#         glider_cluster = MarkerCluster(name="Glider Data").add_to(m)
#         for i, row in glider_df.iterrows():
#             folium.Marker(
#                 location=[row['Lat'], row['Long']],
#                 popup=(
#                     f"<strong>Glider Data</strong><br>"
#                     f"Time: {row['time']}<br>"
#                     f"P2.5: {row['P2_5']} µg/m³<br>"
#                     f"Unknown: {row['unknown']}<br>"
#                     f"P10: {row['P10']} µg/m³<br>"
#                     f"UV: {row['UV']}<br>"
#                     f"CO: {row['CO']} ppm<br>"
#                     f"Fire: {row['Fire']}<br>"
#                     f"H2: {row['H2']}<br>"
#                     f"Temperature: {row['Temp']}°C<br>"
#                     f"Humidity: {row['Hum']}%<br>"
#                     f"Altitude: {row['Alt']} m"
#                 ),
#                 icon=folium.Icon(color='blue')
#             ).add_to(glider_cluster)

#     if show_drone:
#         drone_cluster = MarkerCluster(name="Drone Data").add_to(m)
#         for i, row in drone_df.iterrows():
#             folium.Marker(
#                 location=[row['Lat'], row['Long']],
#                 popup=(
#                     f"<strong>Drone Data</strong><br>"
#                     f"Timestamp: {row['Timestamp']}<br>"
#                     f"Millis: {row['Millis']} ms<br>"
#                     f"Particles > 0.3µm: {row['Particles>0.3um']}<br>"
#                     f"Particles > 0.5µm: {row['Particles>0.5um']}<br>"
#                     f"Particles > 1.0µm: {row['Particles>1.0um']}<br>"
#                     f"Particles > 2.5µm: {row['Particles>2.5um']}<br>"
#                     f"Particles > 5.0µm: {row['Particles>5.0um']}<br>"
#                     f"Particles > 10.0µm: {row['Particles>10.0um']}<br>"
#                     f"PM1.0: {row['PM1.0']} µg/m³<br>"
#                     f"PM2.5: {row['PM2.5']} µg/m³<br>"
#                     f"PM10: {row['PM10']} µg/m³<br>"
#                     f"Humidity: {row['Humidity']}%<br>"
#                     f"Temperature: {row['Temperature']}°C<br>"
#                     f"Flight Iteration: {row['flight_iteration']}<br>"
#                     f"Altitude: {row['Alt']} m"
#                 ),
#                 icon=folium.Icon(color='red')
#             ).add_to(drone_cluster)

#     # Add layer control
#     folium.LayerControl().add_to(m)
    
#     return m

# # Streamlit app
# def main():
#     st.title("Glider and Drone Data Visualization")

#     # Specify file paths directly
#     glider_file = '/Users/petra/Desktop/glider.csv'
#     drone_file = '/Users/petra/Desktop/drone.csv'

#     # Load data without uploading
#     glider_data, drone_data = load_data(glider_file, drone_file)
    
#     # Checkbox for toggling visibility
#     show_glider = st.checkbox("Show Glider Data", value=True)
#     show_drone = st.checkbox("Show Drone Data", value=True)

#     # Create and display map
#     folium_map = create_map(glider_data, drone_data, show_glider, show_drone)
    
#     # Save the map to an HTML file and display it
#     folium_map.save("map.html")
#     st.components.v1.html(open("map.html", "r").read(), width=800, height=600, scrolling=True)

# if __name__ == "__main__":
#     main()




# import pandas as pd
# import folium
# from streamlit_folium import st_folium
# import streamlit as st

# # Function to load CSV data
# def load_data(glider_file, drone_file):
#     # Load glider data
#     glider_df = pd.read_csv(glider_file)
#     glider_df.columns = ['Unnamed: 0', 'time', 'P2_5', 'unknown', 'P10', 'UV', 'CO', 'Fire', 'H2', 'Temp', 'Hum', 'Lat', 'Long', 'Alt']

#     # Load drone data
#     drone_df = pd.read_csv(drone_file, delimiter=';')
#     drone_df.columns = ['Unnamed: 0', 'Timestamp', 'Millis', 'Particles>0.3um', 'Particles>0.5um', 'Particles>1.0um', 'Particles>2.5um', 
#                         'Particles>5.0um', 'Particles>10.0um', 'PM1.0', 'PM2.5', 'PM10', 'Humidity', 'Temperature', 
#                         'flight_iteration', 'Lat', 'Long', 'Alt']
    
#     return glider_df, drone_df

# # Function to plot data points on the map
# def create_map(glider_df, drone_df, visible_layers):
#     # Create base map centered on average lat/long of both datasets
#     if not glider_df.empty and not drone_df.empty:
#         map_center = [(glider_df['Lat'].mean() + drone_df['Lat'].mean()) / 2, 
#                       (glider_df['Long'].mean() + drone_df['Long'].mean()) / 2]
#     else:
#         map_center = [0, 0]  # Default center for empty data
    
#     m = folium.Map(location=map_center, zoom_start=10)

#     # Add Glider Data Points (if selected)
#     if 'Glider Data' in visible_layers:
#         for i, row in glider_df.iterrows():
#             folium.CircleMarker(
#                 location=[row['Lat'], row['Long']],
#                 radius=5,
#                 color='blue',
#                 fill=True,
#                 fill_color='blue',
#                 popup=f"Glider: Time={row['time']}, Temp={row['Temp']}, Humidity={row['Hum']}, Alt={row['Alt']}"
#             ).add_to(m)

#     # Add Drone Data Points (if selected)
#     if 'Drone Data' in visible_layers:
#         for i, row in drone_df.iterrows():
#             folium.CircleMarker(
#                 location=[row['Lat'], row['Long']],
#                 radius=5,
#                 color='red',
#                 fill=True,
#                 fill_color='red',
#                 popup=f"Drone: Time={row['Timestamp']}, Temp={row['Temperature']}, Humidity={row['Humidity']}, Alt={row['Alt']}"
#             ).add_to(m)
    
#     return m

# # Streamlit app layout
# st.title("Glider and Drone Data Map")

# # Load Data
# glider_data, drone_data = load_data('/Users/petra/Desktop/glider.csv', '/Users/petra/Desktop/drone.csv')

# # Display the data for debugging
# st.write("Glider Data", glider_data.head())
# st.write("Drone Data", drone_data.head())

# # Check if the DataFrames are empty
# if glider_data.empty:
#     st.write("Glider data is empty.")
# if drone_data.empty:
#     st.write("Drone data is empty.")

# # Create checkboxes for layer selection
# show_glider_data = st.sidebar.checkbox("Show Glider Data", value=True)
# show_drone_data = st.sidebar.checkbox("Show Drone Data", value=True)

# # Create the map with selected layers
# visible_layers = []
# if show_glider_data:
#     visible_layers.append('Glider Data')
# if show_drone_data:
#     visible_layers.append('Drone Data')

# # Create and display the map
# map_display = create_map(glider_data, drone_data, visible_layers)
# st_folium(map_display, width=700, height=500)



# import pandas as pd
# import folium
# from folium.plugins import HeatMap
# import ipywidgets as widgets
# from IPython.display import display

# # Function to load CSV data
# def load_data(glider_file, drone_file):
#     # Load glider data
#     glider_df = pd.read_csv(glider_file)
#     glider_df.columns = ['Unnamed: 0','time', 'P2_5', 'unknown', 'P10', 'UV', 'CO', 'Fire', 'H2', 'Temp', 'Hum', 'Lat', 'Long', 'Alt']

#     # print(glider_df.head())  # Display the first few rows to check the columns
#     # print(glider_df.columns)  # Print column names

    
#     # Load drone data
#     drone_df = pd.read_csv(drone_file, delimiter=';')
#     drone_df.columns = ['Unnamed: 0', 'Timestamp', 'Millis', 'Particles>0.3um', 'Particles>0.5um', 'Particles>1.0um', 'Particles>2.5um', 
#                         'Particles>5.0um', 'Particles>10.0um', 'PM1.0', 'PM2.5', 'PM10', 'Humidity', 'Temperature', 
#                         'flight_iteration', 'Lat', 'Long', 'Alt']
    
#     # print(drone_df.head())  # Display the first few rows to check the columns
#     # print(drone_df.columns)  # Print column names
    
#     return glider_df, drone_df

# # Function to plot data points on the map
# def create_map(glider_df, drone_df, visible_layers):
#     # Create base map centered on average lat/long of both datasets
#     map_center = [(glider_df['Lat'].mean() + drone_df['Lat'].mean()) / 2, 
#                   (glider_df['Long'].mean() + drone_df['Long'].mean()) / 2]
    
#     m = folium.Map(location=map_center, zoom_start=10)

#     # Add Glider Data Points (if selected)
#     if 'Glider Data' in visible_layers:
#         for i, row in glider_df.iterrows():
#             folium.CircleMarker(
#                 location=[row['Lat'], row['Long']],
#                 radius=5,
#                 color='blue',
#                 fill=True,
#                 fill_color='blue',
#                 popup=f"Glider: Time={row['time']}, Temp={row['Temp']}, Humidity={row['Hum']}, Alt={row['Alt']}"
#             ).add_to(m)

#     # Add Drone Data Points (if selected)
#     if 'Drone Data' in visible_layers:
#         for i, row in drone_df.iterrows():
#             folium.CircleMarker(
#                 location=[row['Lat'], row['Long']],
#                 radius=5,
#                 color='red',
#                 fill=True,
#                 fill_color='red',
#                 popup=f"Drone: Time={row['Timestamp']}, Temp={row['Temperature']}, Humidity={row['Humidity']}, Alt={row['Alt']}"
#             ).add_to(m)
    
#     return m

# # Function to update the map based on layer selection
# def update_map(change):
#     selected_layers = [k for k, v in layer_checkboxes.items() if v.value]
#     updated_map = create_map(glider_data, drone_data, selected_layers)
#     display(updated_map)

# # Load Data
# glider_data, drone_data = load_data('/Users/petra/Desktop/glider.csv', '/Users/petra/Desktop/drone.csv')

# # Create checkboxes for layer selection
# layer_checkboxes = {
#     'Glider Data': widgets.Checkbox(value=True, description='Glider Data'),
#     'Drone Data': widgets.Checkbox(value=True, description='Drone Data')
# }

# # Display checkboxes for selection
# checkbox_widgets = widgets.VBox([layer_checkboxes['Glider Data'], layer_checkboxes['Drone Data']])
# display(checkbox_widgets)

# # Add observers to checkboxes
# for checkbox in layer_checkboxes.values():
#     checkbox.observe(update_map, names='value')

# # Initial Map
# initial_map = create_map(glider_data, drone_data, ['Glider Data', 'Drone Data'])
# display(initial_map)
