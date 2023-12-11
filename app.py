import streamlit as st
import pandas as pd
from datetime import date, datetime
from meteostat import Point, Daily

from datetime import timedelta

# für forecasting

from statsmodels.tsa.api import SimpleExpSmoothing

from prophet import Prophet

import seaborn as sns
from matplotlib import pyplot as plt

import plotly.express as px
import plotly.graph_objects as go

from streamlit_option_menu import option_menu

st.set_page_config(layout="wide")


st.title("Simple Weather Data")
st.info("Sources - historical data: https://meteostat.net, current data: https://open-meteo.com ")




#---Option Menu -------------------


option = option_menu(
	menu_title="",
	options=["Today", "This week","History","Prediction"],
	icons=["calendar-event", "calendar-week","clock-history","pip"], #https://icons.getbootstrap.com/
	orientation="horizontal",
)

import openmeteo_requests

import requests_cache

from retry_requests import retry


# Code um den Button-Design anzupassen
m = st.markdown("""
<style>
div.stButton > button:first-child {
    background-color: #ce1126;
    color: white;
    height: 3em;
    width: 10em;
    border-radius:10px;
    border:3px solid #000000;
    font-size:20px;
    font-weight: bold;
    margin: auto;
    display: block;
}
div.stButton > button:hover {
	background:linear-gradient(to bottom, #ce1126 5%, #ff5a5a 100%);
	background-color:#ce1126;
}
div.stButton > button:active {
	position:relative;
	top:3px;
}
</style>""", unsafe_allow_html=True)

# === Variables mit session state ====#

if 'checkWeather' not in st.session_state:
    st.session_state.checkWeather = False

if 'forecastHorizonSpeicher' not in st.session_state:
    st.session_state.forecastHorizonSpeicher = 24
if 'forecastFreqSpeicher' not in st.session_state:
    st.session_state.forecastFreqSpeicher = "M"
if 'forecastVariableSpeicher' not in st.session_state:
    st.session_state.forecastVariableSpeicher = "tavg"

if 'ortsEingabeSpeicher' not in st.session_state:
    st.session_state.ortsEingabeSpeicher = "Zurich"



########################################

_ = """
# find nearest weatherstation - based on ip location and set this as default
import geocoder
import reverse_geocoder as rg

g = geocoder.ip('me')
lat = (g.lat)
long = (g.lng)

from meteostat import Stations

stationNearby = Stations()
stationNearby = stationNearby.nearby(lat, long)
stationNearby = stationNearby.fetch(1)
weatherstation_data = pd.DataFrame(stationNearby)
nearestWeatherstation = weatherstation_data['name'].iloc[0]
# st.write("stationNearby: ",stationNearby)



from geopy.geocoders import Nominatim
geolocator = Nominatim(user_agent="nearest-town-finder")
location = geolocator.reverse((lat, long), exactly_one=True)
if location:
    nearest_town = location.address.split(",")[2].strip()
    st.write("nearest_town:", nearest_town)
"""
_ = """
coordinates = (lat, long)
searchLokalInfo = rg.search(coordinates)
searchLokalInfo_name = [x.get('name') for x in searchLokalInfo]
st.write("searchLokalInfo_name: ",searchLokalInfo_name)
Town = searchLokalInfo_name[0]
st.write("Town: ",Town)
"""


today = date.today()
last_year = today - timedelta(days=365 * 5)
# st.write("last_year: ", last_year)


# Import the required library
from geopy.geocoders import Nominatim

from meteostat import Stations


# Initialize Nominatim API
geolocator = Nominatim(user_agent="MyApp")


with st.sidebar.form("Enter Location"): ##############################################

    st.write("")
    Ortseingabe = st.text_input("Enter location:", value=st.session_state.ortsEingabeSpeicher)
    st.session_state.ortsEingabeSpeicher = Ortseingabe
    st.write("")

    location = geolocator.geocode(Ortseingabe)



    stations = Stations()
    stations = stations.nearby(location.latitude, location.longitude)
    station = stations.fetch(1)
    weatherstation_data = pd.DataFrame(station)
    nearestWeatherstation = weatherstation_data['name'].iloc[0]
    nearestWeatherstation_latitude = weatherstation_data['latitude'].iloc[0]
    nearestWeatherstation_longitude = weatherstation_data['longitude'].iloc[0]
    nearestWeatherstation_elevation = weatherstation_data['elevation'].iloc[0]

    locationInfoExpander = st.sidebar.expander("Location info")
    with locationInfoExpander:
        st.write(location.raw)
        st.write("The latitude of the location is: ", location.latitude)
        st.write("The longitude of the location is: ", location.longitude)
        st.write("Nearest Weather Station (Meteostat): ", weatherstation_data)


    mapdata = {
        'LATITUDEPOINTS': [nearestWeatherstation_latitude, location.latitude],
        'LONGITUDEPOINTS': [nearestWeatherstation_longitude, location.longitude],
        'name': ['Nearest Weatherstation', 'Location']
    }

    df_mapOrte = pd.DataFrame(mapdata)

    # Display a map with multiple points
    st.sidebar.map(df_mapOrte, latitude='LATITUDEPOINTS', longitude='LONGITUDEPOINTS',size=40)


    historySettingsExpander = st.expander("History settings")
    with historySettingsExpander:
        #st.write("History settings")

        startInput = st.date_input("Start Date", date(2018, 1, 1), key="start")
        # startInput = st.date_input("Start Date",last_year, key="start")

        # endInput = st.date_input("End Date", date(2023, 7, 22))
        endInput = st.date_input("End Date", today, key="end")

        heightInput = st.number_input('Elevation (default - elevation of weather station)',
                                  value=nearestWeatherstation_elevation)

    # Convert datetime.date objects to datetime.datetime objects
    startInput = datetime(startInput.year, startInput.month, startInput.day)
    endInput = datetime(endInput.year, endInput.month, endInput.day)

    Ort = Point(nearestWeatherstation_latitude, nearestWeatherstation_longitude, heightInput)

    data = Daily(Ort, startInput, endInput)

    #ProphetforecastStarten = st.toggle("Forecast with Prophet", key="forecast")
    ProphetforecastStarten= True


    forecastSettingsExpander = st.expander("Prediction settings")
    with forecastSettingsExpander:
        st.write("Prophet Forecast")

        fcol2, fcol3 = st.columns(2)

        forecastHorizon = st.slider("Periods", min_value=1, value=st.session_state.forecastHorizonSpeicher)
        st.session_state.forecastHorizonSpeicher = forecastHorizon

        with fcol2:
            freqEingabe = st.selectbox("Frequency", ["D", "W", "M", "Q", "Y"],
                                   index=2)

        # using pop(0) to perform removal of first item
        # forecastValueListe.pop(0)

        with fcol3:
            #forecastValueListe = data.columns.to_list()
            forecastVariable = st.selectbox("Variable", ["tavg", "tmin","tmax","prcp","snow","wspd"],index=0)




    st.subheader("")
    #checkButton = st.form_submit_button("Check weather data!") ###########################
    st.session_state.checkWeather = st.form_submit_button("Check!")
    st.subheader("")

#if checkButton == True:
if st.session_state.checkWeather == True:
    st.session_state.ortsEingabeSpeicher = Ortseingabe

    data = data.fetch()

    if (len(data)) == 0:
        st.sidebar.warning("No weather data found for \n" + str(location))
        st.stop()

    data.reset_index()

    data["Date"] = (data.index)

    # Using pandas.Series.dt.year()
    data['Year'] = data['Date'].dt.year

    # get value of last row
    todayAverage = data['tavg'].iloc[-1]
    todayMin = data['tmin'].iloc[-1]
    todayMax = data['tmax'].iloc[-1]
    todayWspd = data['wspd'].iloc[-1] * 0.277778
    todayMaxText = str(todayMax) + " °C"
    todayMinText = str(todayMin) + " °C"
    todayWspdText = str(todayWspd.round(1)) + " m/s"
    todayMaxMinDiff = todayMax - todayMin
    # st.write(todayMax)
    #st.sidebar.write(today)
    #st.sidebar.metric(label="Today's Max Temperature in  \n" + str(nearestWeatherstation), value=todayMaxText,
                     # delta=todayMaxMinDiff.round(1))
    #st.sidebar.metric(label="Today's Min Temperature", value=todayMinText)
    #st.sidebar.metric(label="Today's Windspeed", value=todayWspdText)




    #OPENMETEO  ##############################################################################################




    # Setup the Open-Meteo API client with cache and retry on error
    cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)

    # Make sure all required weather variables are listed here
    # The order of variables in hourly or daily is important to assign them correctly below
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": location.latitude,
        "longitude": location.longitude,
        "current": ["temperature_2m", "precipitation", "rain", "showers", "snowfall", "wind_speed_10m",
                    "wind_direction_10m"],
        "hourly": ["temperature_2m", "precipitation_probability", "precipitation", "rain", "snowfall",
                   "cloud_cover_high", "wind_speed_10m"],
        "daily": ["temperature_2m_max", "temperature_2m_min", "sunrise", "sunset", "daylight_duration",
                  "sunshine_duration", "precipitation_sum", "rain_sum", "showers_sum", "snowfall_sum",
                  "precipitation_hours", "wind_speed_10m_max", "wind_gusts_10m_max", "wind_direction_10m_dominant"],
        "wind_speed_unit": "ms"
    }
    responses = openmeteo.weather_api(url, params=params)

    # Process first location. Add a for-loop for multiple locations or weather models
    response = responses[0]
    #st.write(f"Coordinates {response.Latitude()}°E {response.Longitude()}°N")
    #st.write(f"Elevation {response.Elevation()} m asl")
    #st.write(f"Timezone {response.Timezone()} {response.TimezoneAbbreviation()}")
    #st.write(f"Timezone difference to GMT+0 {response.UtcOffsetSeconds()} s")

    # Current values. The order of variables needs to be the same as requested.
    current = response.Current()
    current_temperature_2m = current.Variables(0).Value()
    current_precipitation = current.Variables(1).Value()
    current_rain = current.Variables(2).Value()
    current_showers = current.Variables(3).Value()
    current_snowfall = current.Variables(4).Value()
    current_wind_speed_10m = current.Variables(5).Value()
    current_wind_direction_10m = current.Variables(6).Value()

    _="""
    st.write(f"Current time {current.Time()}")
    st.write(f"Current temperature_2m {current_temperature_2m}")
    st.write(f"Current precipitation {current_precipitation}")
    st.write(f"Current rain {current_rain}")
    st.write(f"Current showers {current_showers}")
    st.write(f"Current snowfall {current_snowfall}")
    st.write(f"Current wind_speed_10m {current_wind_speed_10m}")
    st.write(f"Current wind_direction_10m {current_wind_direction_10m}")
    """

    current_wind_speed_text = str(round(current_wind_speed_10m,1)) + " m/s"

    current_temperature_text = str(round(current_temperature_2m,1)) + " °C"

    current_rain_text =  str(round(current_rain,1)) + " mm"

    if option == "Today": ############################

        st.subheader("")
        st.subheader("Today's weather forecast data for " + Ortseingabe)

        #st.sidebar.divider()
        #st.sidebar.write(f"Current rain {current_rain}")

        todayMetricCol1,todayMetricCol2,todayMetricCol3,todayMetricCol4 = st.columns(4)
        with todayMetricCol1:
            st.metric(label="Current temperature in  \n" + Ortseingabe, value=current_temperature_text)
        with todayMetricCol2:
            st.metric(label="Current rain", value=current_rain_text)
        with todayMetricCol3:
            st.metric(label="Current wind speed", value=current_wind_speed_text)
        with todayMetricCol4:
            st.metric(label="Current wind direction", value=round(current_wind_direction_10m,0))
        st.subheader("")
        #st.sidebar.map(data=None, latitude=nearestWeatherstation_latitude, longitude=nearestWeatherstation_longitude, color="red", size=10, zoom=16, use_container_width=True)
        # Display a map centered at the given latitude and longitude
        #st.sidebar.map((nearestWeatherstation_latitude, nearestWeatherstation_longitude), zoom=12)
        # Sample data with latitude and longitude
        #latitude = 37.7749  # Sample latitude (San Francisco)
        #longitude = -122.4194  # Sample longitude (San Francisco)
        # Display a map centered at the given latitude and longitude
        #st.sidebar.map(latitude=nearestWeatherstation_latitude, longitude=nearestWeatherstation_longitude, zoom=12)



        # Process hourly data. The order of variables needs to be the same as requested.
        hourly = response.Hourly()
        hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()
        hourly_precipitation_probability = hourly.Variables(1).ValuesAsNumpy()
        hourly_precipitation = hourly.Variables(2).ValuesAsNumpy()
        hourly_rain = hourly.Variables(3).ValuesAsNumpy()
        hourly_snowfall = hourly.Variables(4).ValuesAsNumpy()
        hourly_cloud_cover_high = hourly.Variables(5).ValuesAsNumpy()
        hourly_wind_speed_10m = hourly.Variables(6).ValuesAsNumpy()

        hourly_data = {"date": pd.date_range(
            start=pd.to_datetime(hourly.Time(), unit="s"),
            end=pd.to_datetime(hourly.TimeEnd(), unit="s"),
            freq=pd.Timedelta(seconds=hourly.Interval()),
            inclusive="left"
        )}
        hourly_data["temperature_2m"] = hourly_temperature_2m
        hourly_data["precipitation_probability"] = hourly_precipitation_probability
        hourly_data["precipitation"] = hourly_precipitation
        hourly_data["rain"] = hourly_rain
        hourly_data["snowfall"] = hourly_snowfall
        hourly_data["cloud_cover_high"] = hourly_cloud_cover_high
        hourly_data["wind_speed_10m"] = hourly_wind_speed_10m


        hourly_dataframe = pd.DataFrame(data=hourly_data)
        st.info("Hourly data from Open-Meteo.com")

        hourlyExpander = st.expander("Tables with hourly data for 3 days >>>")
        with hourlyExpander:
            st.write(hourly_dataframe)


        hourlyCols1, hourCols2 = st.columns(2)

        with hourlyCols1:
            st.info("Today's Temperatures")
            todaytemp_data = pd.DataFrame(
                hourly_dataframe,
                columns=['date','temperature_2m'])
            todaytemp_data = todaytemp_data.head(24)
            st.line_chart(todaytemp_data.temperature_2m,use_container_width=True)

        with hourCols2:
            todayrain_data = pd.DataFrame(
                hourly_dataframe,
                columns=['date','rain'])
            todayrain_data = todayrain_data.head(24)
            todayRainVorkommen = todayrain_data.rain.sum()
            if todayRainVorkommen:
                st.info("Today's rain")
                st.bar_chart(todayrain_data.rain,use_container_width=True)


        hourlyCols3, hourlyCols4 = st.columns(2)
        with hourlyCols3:
            st.info("Today's wind")
            todaywind_data = pd.DataFrame(
                hourly_dataframe,
                columns=['date','wind_speed_10m'])
            todaywind_data = todaywind_data.head(24)
            st.line_chart(todaywind_data.wind_speed_10m,use_container_width=True)

        with hourlyCols4:
            todaysnow_data = pd.DataFrame(
                hourly_dataframe,
                columns=['date','snowfall'])
            todaysnow_data = todaysnow_data.head(24)
            todaysnowVorkommen = todaysnow_data.snowfall.sum()
            if todaysnowVorkommen > 0:
                st.info("Today's snowfall")
                st.bar_chart(todaysnow_data.snowfall,use_container_width=True)



    if option == "This week": ############################

        # Process daily data. The order of variables needs to be the same as requested.
        daily = response.Daily()
        daily_temperature_2m_max = daily.Variables(0).ValuesAsNumpy()
        daily_temperature_2m_min = daily.Variables(1).ValuesAsNumpy()
        daily_sunrise = daily.Variables(2).ValuesAsNumpy()
        daily_sunset = daily.Variables(3).ValuesAsNumpy()
        daily_daylight_duration = daily.Variables(4).ValuesAsNumpy()
        daily_sunshine_duration = daily.Variables(5).ValuesAsNumpy()
        daily_precipitation_sum = daily.Variables(6).ValuesAsNumpy()
        daily_rain_sum = daily.Variables(7).ValuesAsNumpy()
        daily_showers_sum = daily.Variables(8).ValuesAsNumpy()
        daily_snowfall_sum = daily.Variables(9).ValuesAsNumpy()
        daily_precipitation_hours = daily.Variables(10).ValuesAsNumpy()
        daily_wind_speed_10m_max = daily.Variables(11).ValuesAsNumpy()
        daily_wind_gusts_10m_max = daily.Variables(12).ValuesAsNumpy()
        daily_wind_direction_10m_dominant = daily.Variables(13).ValuesAsNumpy()

        daily_data = {"date": pd.date_range(
            start=pd.to_datetime(daily.Time(), unit="s"),
            end=pd.to_datetime(daily.TimeEnd(), unit="s"),
            freq=pd.Timedelta(seconds=daily.Interval()),
            inclusive="left"
        )}
        daily_data["temperature_2m_max"] = daily_temperature_2m_max
        daily_data["temperature_2m_min"] = daily_temperature_2m_min
        daily_data["sunrise"] = daily_sunrise
        daily_data["sunset"] = daily_sunset
        daily_data["daylight_duration"] = daily_daylight_duration
        daily_data["sunshine_duration"] = daily_sunshine_duration
        daily_data["precipitation_sum"] = daily_precipitation_sum
        daily_data["rain_sum"] = daily_rain_sum
        daily_data["showers_sum"] = daily_showers_sum
        daily_data["snowfall_sum"] = daily_snowfall_sum
        daily_data["precipitation_hours"] = daily_precipitation_hours
        daily_data["wind_speed_10m_max"] = daily_wind_speed_10m_max
        daily_data["wind_gusts_10m_max"] = daily_wind_gusts_10m_max
        daily_data["wind_direction_10m_dominant"] = daily_wind_direction_10m_dominant

        daily_dataframe = pd.DataFrame(data=daily_data)
        # Create a new column for weekdays
        daily_dataframe['weekday'] = daily_dataframe['date'].dt.day_name()
        daily_dataframe = daily_dataframe.sort_values(by='date')

        st.subheader("This week's weather forecast for " + Ortseingabe)
        st.info("Daily data from Open-Meteo.com")

        dailyExpander = st.expander("Tables with data data for this week >>>")
        with dailyExpander:
            st.write(daily_dataframe)

        dailyCols1, dailyCols2 = st.columns(2)
        with dailyCols1:
            st.info("This weeks Temperatures")
            weektemp_data = pd.DataFrame(
                daily_dataframe,
                columns=['date','weekday','temperature_2m_max','temperature_2m_min'])
            #weektemp_data['weekday'].sort(ascending=True)
            #st.write(weektemp_data)
            #st.line_chart(weektemp_data,x='weekday',y='temperature_2m_max',use_container_width=True)

            figPlotlyLinechart_weektemp_data = px.line(weektemp_data, x='weekday',
                                                       y=['temperature_2m_max','temperature_2m_min'], line_shape='linear',
                                                       # color_discrete_map={'GESAMTReichweite' : FARBE_GESAMT,'TVReichweite' : FARBE_TV,'ZATTOOReichweite' : FARBE_ZATTOO,'KINOReichweite' : FARBE_KINO,'DOOHReichweite' : FARBE_DOOH,'OOHReichweite' : FARBE_OOH,'FACEBOOKReichweite' : FARBE_FACEBOOK,'YOUTUBEReichweite' : FARBE_YOUTUBE,'ONLINEVIDEOReichweite' : FARBE_ONLINEVIDEO,'ONLINEReichweite' : FARBE_ONLINE, 'RADIOReichweite' : FARBE_RADIO},
                                                       # markers=True,
                                                       # Animation:
                                                       # range_x=[0, gesamtBudget*1000],
                                                       #range_y=[0, forecastYhatMax],
                                                       # animation_frame="ds)
                                                       )

            # Change grid color and axis colors
            figPlotlyLinechart_weektemp_data.update_xaxes(showline=True, linewidth=0.1, linecolor='Black',
                                                          gridcolor='Black')
            figPlotlyLinechart_weektemp_data.update_yaxes(showline=True, linewidth=0.1, linecolor='Black',
                                                          gridcolor='Black')

            figPlotlyLinechart_weektemp_data.layout.update(showlegend=True)

            st.plotly_chart(figPlotlyLinechart_weektemp_data, use_container_width=True)




        with dailyCols2:
            weekrain_data = pd.DataFrame(
                daily_dataframe,
                columns=['weekday','rain_sum'])
            #st.write(weekrain_data)
            weekRainVorkommen = weekrain_data.rain_sum.sum()
            if weekRainVorkommen:
                st.info("This week's rain")
                #st.bar_chart(weekrain_data,x='weekday',use_container_width=True)

                figPlotlyBarchart_weekrain_data= px.bar(weekrain_data, x='weekday',
                                                           y='rain_sum',
                                                           # color_discrete_map={'GESAMTReichweite' : FARBE_GESAMT,'TVReichweite' : FARBE_TV,'ZATTOOReichweite' : FARBE_ZATTOO,'KINOReichweite' : FARBE_KINO,'DOOHReichweite' : FARBE_DOOH,'OOHReichweite' : FARBE_OOH,'FACEBOOKReichweite' : FARBE_FACEBOOK,'YOUTUBEReichweite' : FARBE_YOUTUBE,'ONLINEVIDEOReichweite' : FARBE_ONLINEVIDEO,'ONLINEReichweite' : FARBE_ONLINE, 'RADIOReichweite' : FARBE_RADIO},
                                                           # markers=True,
                                                           # Animation:
                                                           # range_x=[0, gesamtBudget*1000],
                                                           # range_y=[0, forecastYhatMax],
                                                           # animation_frame="ds)
                                                           )

                # Change grid color and axis colors
                figPlotlyBarchart_weekrain_data.update_xaxes(showline=True, linewidth=0.1, linecolor='Black',
                                                              gridcolor='Black')
                figPlotlyBarchart_weekrain_data.update_yaxes(showline=True, linewidth=0.1, linecolor='Black',
                                                              gridcolor='Black')

                figPlotlyBarchart_weekrain_data.layout.update(showlegend=False)

                st.plotly_chart(figPlotlyBarchart_weekrain_data, use_container_width=True)


        dailyCols3, dailyCols4 = st.columns(2)

        #wind_speed_10m_max

        with dailyCols3:
            st.info("This week's max wind speeds")
            weekWind_data = pd.DataFrame(
                daily_dataframe,
                columns=['weekday','wind_speed_10m_max'])

            figPlotlyLinechart_weekWind_data = px.line(weekWind_data, x='weekday',
                                                       y='wind_speed_10m_max', line_shape='linear',
                                                       # color_discrete_map={'GESAMTReichweite' : FARBE_GESAMT,'TVReichweite' : FARBE_TV,'ZATTOOReichweite' : FARBE_ZATTOO,'KINOReichweite' : FARBE_KINO,'DOOHReichweite' : FARBE_DOOH,'OOHReichweite' : FARBE_OOH,'FACEBOOKReichweite' : FARBE_FACEBOOK,'YOUTUBEReichweite' : FARBE_YOUTUBE,'ONLINEVIDEOReichweite' : FARBE_ONLINEVIDEO,'ONLINEReichweite' : FARBE_ONLINE, 'RADIOReichweite' : FARBE_RADIO},
                                                       # markers=True,
                                                       # Animation:
                                                       # range_x=[0, gesamtBudget*1000],
                                                       #range_y=[0, forecastYhatMax],
                                                       # animation_frame="ds)
                                                       )

            # Change grid color and axis colors
            figPlotlyLinechart_weekWind_data.update_xaxes(showline=True, linewidth=0.1, linecolor='Black',
                                                          gridcolor='Black')
            figPlotlyLinechart_weekWind_data.update_yaxes(showline=True, linewidth=0.1, linecolor='Black',
                                                          gridcolor='Black')

            figPlotlyLinechart_weekWind_data.layout.update(showlegend=False)

            st.plotly_chart(figPlotlyLinechart_weekWind_data, use_container_width=True)


        with dailyCols4:
            st.info("This week's snow falls")
            weeksnowfall_data = pd.DataFrame(
                daily_dataframe,
                columns=['weekday','snowfall_sum'])

            figPlotlyLinechart_weekSnow_data = px.bar(weeksnowfall_data, x='weekday',
                                                       y='snowfall_sum', #line_shape='linear',
                                                       # color_discrete_map={'GESAMTReichweite' : FARBE_GESAMT,'TVReichweite' : FARBE_TV,'ZATTOOReichweite' : FARBE_ZATTOO,'KINOReichweite' : FARBE_KINO,'DOOHReichweite' : FARBE_DOOH,'OOHReichweite' : FARBE_OOH,'FACEBOOKReichweite' : FARBE_FACEBOOK,'YOUTUBEReichweite' : FARBE_YOUTUBE,'ONLINEVIDEOReichweite' : FARBE_ONLINEVIDEO,'ONLINEReichweite' : FARBE_ONLINE, 'RADIOReichweite' : FARBE_RADIO},
                                                       # markers=True,
                                                       # Animation:
                                                       # range_x=[0, gesamtBudget*1000],
                                                       #range_y=[0, forecastYhatMax],
                                                       # animation_frame="ds)
                                                       )

            # Change grid color and axis colors
            figPlotlyLinechart_weekSnow_data.update_xaxes(showline=True, linewidth=0.1, linecolor='Black',
                                                          gridcolor='Black')
            figPlotlyLinechart_weekSnow_data.update_yaxes(showline=True, linewidth=0.1, linecolor='Black',
                                                          gridcolor='Black')

            figPlotlyLinechart_weekSnow_data.layout.update(showlegend=False)

            st.plotly_chart(figPlotlyLinechart_weekSnow_data, use_container_width=True)



        dailyCols5, dailyCols6 = st.columns(2)
        with dailyCols5:
                #sunshine_duration

                st.info("This week's sunshine")
                weeksunshine_data = pd.DataFrame(
                    daily_dataframe,
                    columns=['weekday', 'sunshine_duration'])

                figPlotlyLinechart_weeksunshine_data = px.bar(weeksunshine_data, x='weekday',
                                                          y=weeksunshine_data.sunshine_duration/3600,  # line_shape='linear',
                                                          # color_discrete_map={'GESAMTReichweite' : FARBE_GESAMT,'TVReichweite' : FARBE_TV,'ZATTOOReichweite' : FARBE_ZATTOO,'KINOReichweite' : FARBE_KINO,'DOOHReichweite' : FARBE_DOOH,'OOHReichweite' : FARBE_OOH,'FACEBOOKReichweite' : FARBE_FACEBOOK,'YOUTUBEReichweite' : FARBE_YOUTUBE,'ONLINEVIDEOReichweite' : FARBE_ONLINEVIDEO,'ONLINEReichweite' : FARBE_ONLINE, 'RADIOReichweite' : FARBE_RADIO},
                                                          # markers=True,
                                                          # Animation:
                                                          # range_x=[0, gesamtBudget*1000],
                                                          # range_y=[0, forecastYhatMax],
                                                          # animation_frame="ds)
                                                          )

                # Change grid color and axis colors
                figPlotlyLinechart_weeksunshine_data.update_xaxes(showline=True, linewidth=0.1, linecolor='Black',
                                                              gridcolor='Black')
                figPlotlyLinechart_weeksunshine_data.update_yaxes(showline=True, linewidth=0.1, linecolor='Black',
                                                              gridcolor='Black')

                figPlotlyLinechart_weeksunshine_data.layout.update(showlegend=False)

                st.plotly_chart(figPlotlyLinechart_weeksunshine_data, use_container_width=True)

        with dailyCols6:
                st.write("")

    ###############################################################################################



    if option == "History": ############################

        st.subheader("")
        st.title("Historical data for " + Ortseingabe)

        st.info("Nearest weatherstation: " + nearestWeatherstation)
        st.subheader("")

        data_YearAvg = data.groupby('Year').agg({'tavg': 'mean'})['tavg']

        data_YearMax = data.groupby('Year').agg({'tmax': 'max'})['tmax']

        data_YearMin = data.groupby('Year').agg({'tmin': 'min'})['tmin']

        data_YearWspd = data.groupby('Year').agg({'wspd': 'mean'})['wspd']

        data_YearWprcp = data.groupby('Year').agg({'prcp': 'mean'})['prcp']

        data_Yearsnow = data.groupby('Year').agg({'snow': 'mean'})['snow']

        st.info("Yearly Averages from Meteostat.net")

        if len(data_YearAvg) > 1:
            col1, col2, col3, col4, col5, col6 = st.columns(6)
            with col1:
                st.write("Average Temperatures")
                st.write(data_YearAvg)
            with col2:
                st.write("Max Temperatures")
                st.write(data_YearMax)

            with col3:
                st.write("Min Temperatures")
                st.write(data_YearMin)

            with col4:
                st.write("Average Windspeeds")
                st.write(data_YearWspd)

            with col5:
                st.write("Average Preciptation")
                st.write(data_YearWprcp)

            with col6:
                st.write("Snowfall")
                st.write(data_Yearsnow)

        # data_YearAvg['Max'] = data_YearMax['tmax']

        # data["Year"] = data.Date.str.split(' ').str[1]

        ShowAllDataExpander = st.expander("Show Table with all data >>>")
        with ShowAllDataExpander:
            st.write(data)

        st.subheader("")
        st.info("Average Temperatures")
        tavg_data = pd.DataFrame(
            data,
            columns=['tavg'])

        st.line_chart(tavg_data, use_container_width=True)

        st.subheader("")
        st.info("Min/Max Temperatures")
        tMinMax_data = pd.DataFrame(
            data,
            columns=['tmax', 'tmin'])
        st.line_chart(tMinMax_data, use_container_width=True)

        st.subheader("")
        st.info("Average Windspeed")
        wspd_data = pd.DataFrame(
            data,
            columns=['wspd'])

        st.line_chart(wspd_data, use_container_width=True)

        st.subheader("")
        st.info("Preciptation")
        prcp_data = pd.DataFrame(
            data,
            columns=['prcp'])

        st.bar_chart(prcp_data, use_container_width=True)

        snow_data = pd.DataFrame(
            data,
            columns=['snow'])

        if snow_data['snow'].sum() > 0:
            st.subheader("")
            st.info("Snow")
            st.bar_chart(snow_data, use_container_width=True)

        _ = """
        st.info("Air Pressure")
        pres_data = pd.DataFrame(
            data,
            columns=['pres'])
        st.line_chart(pres_data, use_container_width=True)
        """



    # FORECASTING mit Prophet ##############################################################

    if option == "Prediction": ############################
        if ProphetforecastStarten:
            #st.sidebar.subheader("")
            #st.sidebar.divider()
            #st.sidebar.subheader("")
            #ProphetforecastStarten = st.sidebar.toggle("Forecast with Prophet", key="forecast")

            if (len(data)) < 20:
                st.warning("Not enough data for meaningfull statistical forecasting with Prophet, change time range")

            if (len(data)) >= 20:
                st.subheader("")

                st.title("Prophet Forecast")

                st.info(
                    "Prophet is a time series forecasting tool developed by Facebook that is widely used for predicting future values based on historical data. It is designed to handle data with strong seasonal patterns and missing values. Prophet employs an additive model that decomposes time series data into components such as trend, seasonality, and holidays, allowing for more accurate predictions. It incorporates customizable parameters to adjust the sensitivity to different patterns in the data")

                #with st.form("Settings"):

                _="""
                fcol1, fcol2, fcol3 = st.columns(3)
    
                with fcol1:
                    forecastHorizon = st.slider("Forecastperiods", min_value=1, value=st.session_state.forecastHorizonSpeicher)
                    st.session_state.forecastHorizonSpeicher = forecastHorizon
    
                with fcol2:
                    freqEingabe = st.selectbox("Select the frequency of the forecast", ["D", "W", "M", "Q", "Y"],
                                                   index=2)
    
    
                # using pop(0) to perform removal of first item
                # forecastValueListe.pop(0)
    
                with fcol3:
                    forecastValueListe = data.columns.to_list()
                    forecastVariable = st.selectbox(
                    'Value to forecast?', forecastValueListe)
                """

                #submittedSettings = st.form_submit_button("Update")
                #submittedSettings = st.checkbox("Update")
                submittedSettings = True
                if submittedSettings == True:

                    df_ProphetForecastAuswahl = data.rename(columns={'Date': 'ds', forecastVariable: 'y'})

                    # st.write(df_ProphetForecastAuswahl)

                    # Create a Prophet model
                    m = Prophet()

                    # Fit the model to the data
                    m.fit(df_ProphetForecastAuswahl)

                    # Make future predictions
                    future = m.make_future_dataframe(periods=forecastHorizon,
                                                     freq=freqEingabe)  # freq M heisst wohl monatliche Werte
                    Prohetforecast_df = m.predict(future)


                    forecastDateExpander = st.expander("Tables with Forecast Data >>")
                    with forecastDateExpander:
                        st.write('Forecast Data:')
                        # Display the forecast output
                        st.write(Prohetforecast_df)
                        st.write(Prohetforecast_df.describe())

                    forecastYhatMax = Prohetforecast_df['yhat'].max() * 1.2

                    st.subheader("Forecast of " + forecastVariable)

                    fig1 = m.plot(Prohetforecast_df)
                    st.write(fig1)

                    fig2 = m.plot_components(Prohetforecast_df)
                    st.write(fig2)

                    data_Prohetforecast_df = data.merge(
                        Prohetforecast_df,
                        left_on='Date',
                        right_on='ds',
                        how='right'  # You can choose 'inner', 'outer', 'left', or 'right' depending on your requirements
                    )

                    data_Prohetforecast_dfExpander = st.expander("Show Measured and forecasted data >>")
                    with data_Prohetforecast_dfExpander:
                        st.write("data_Prohetforecast_df:", data_Prohetforecast_df)

                    st.subheader("")

                    st.subheader("Forecast (yhat) und real data -  " + forecastVariable)

                    # lineShapeAuswahl = 'spline'

                    # if st.checkbox("Linear line shape", key="monthlySpendingsAll"):
                    #   lineShapeAuswahl = 'linear'

                    figPlotlyLinechart_data_forecast = px.line(data_Prohetforecast_df, x='ds',
                                                               y=['yhat', forecastVariable, 'trend'], line_shape='linear',
                                                               # color_discrete_map={'GESAMTReichweite' : FARBE_GESAMT,'TVReichweite' : FARBE_TV,'ZATTOOReichweite' : FARBE_ZATTOO,'KINOReichweite' : FARBE_KINO,'DOOHReichweite' : FARBE_DOOH,'OOHReichweite' : FARBE_OOH,'FACEBOOKReichweite' : FARBE_FACEBOOK,'YOUTUBEReichweite' : FARBE_YOUTUBE,'ONLINEVIDEOReichweite' : FARBE_ONLINEVIDEO,'ONLINEReichweite' : FARBE_ONLINE, 'RADIOReichweite' : FARBE_RADIO},
                                                               # markers=True,
                                                               # Animation:
                                                               # range_x=[0, gesamtBudget*1000],
                                                               range_y=[0, forecastYhatMax],
                                                               # animation_frame="ds)
                                                               )

                    # Change grid color and axis colors
                    figPlotlyLinechart_data_forecast.update_xaxes(showline=True, linewidth=0.1, linecolor='Black',
                                                                  gridcolor='Black')
                    figPlotlyLinechart_data_forecast.update_yaxes(showline=True, linewidth=0.1, linecolor='Black',
                                                                  gridcolor='Black')

                    st.plotly_chart(figPlotlyLinechart_data_forecast, use_container_width=True)

                    # Group by the year and calculate the average prognostizierte values

                    st.write("forecastVariable: ",forecastVariable)

                    #average_Values_per_year = data_Prohetforecast_df.groupby('Year')['yhat', forecastVariable].mean()
                    average_Values_per_year = data_Prohetforecast_df.groupby('Year')[['yhat', forecastVariable]].mean()

                    if len(average_Values_per_year) > 1:
                        # st.write(average_Values_per_year)

                        st.subheader("Prophet Forecast (yhat) und measured values for " + forecastVariable + " per Year")
                        figPlotlyBarChartaverage_Values_per_year = px.bar(average_Values_per_year,
                                                                          x=average_Values_per_year.index,
                                                                          y=['yhat', forecastVariable], barmode='group',
                                                                          # color_discrete_map={'GESAMTReichweite' : FARBE_GESAMT,'TVReichweite' : FARBE_TV,'ZATTOOReichweite' : FARBE_ZATTOO,'KINOReichweite' : FARBE_KINO,'DOOHReichweite' : FARBE_DOOH,'OOHReichweite' : FARBE_OOH,'FACEBOOKReichweite' : FARBE_FACEBOOK,'YOUTUBEReichweite' : FARBE_YOUTUBE,'ONLINEVIDEOReichweite' : FARBE_ONLINEVIDEO,'ONLINEReichweite' : FARBE_ONLINE, 'RADIOReichweite' : FARBE_RADIO},
                                                                          # markers=True,
                                                                          # Animation:
                                                                          # range_x=[0, gesamtBudget*1000],
                                                                          # range_y=[0, forecastYhatMax],
                                                                          # animation_frame="ds)
                                                                          )

                        # Change grid color and axis colors
                        figPlotlyBarChartaverage_Values_per_year.update_xaxes(showline=True, linewidth=0.1, linecolor='Black',
                                                                              gridcolor='Black')
                        figPlotlyBarChartaverage_Values_per_year.update_yaxes(showline=True, linewidth=0.1, linecolor='Black',
                                                                              gridcolor='Black')

                        st.plotly_chart(figPlotlyBarChartaverage_Values_per_year, use_container_width=True)

                        average_Values_per_year['Difference %'] = 100 * (((average_Values_per_year['yhat'] /
                                                                           average_Values_per_year[forecastVariable]).round(
                            3)) - 1)

                        average_Values_per_yearTabelle = average_Values_per_year.T

                        st.write("Difference of Yearly averages  - Prediction yhat vs measurements of " + forecastVariable,
                                 average_Values_per_yearTabelle)





        ############ KORRELATIONEN #######################

        if (len(data)) > 0:
            st.subheader("")
            st.subheader("")
            st.subheader("Correlations")
            korrelationenExpander = st.expander("Show correlations >>")
            with korrelationenExpander:
                st.write(data.corr())

                st.subheader("")

                st.write("Correlation Heatmap")
                fig, ax = plt.subplots()
                sns.heatmap(data.corr(), annot=False, cmap='RdBu')
                plt.title('Correlation Heatmap')  # ,fontsize=8)
                st.write(fig)

                st.subheader("")