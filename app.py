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

st.set_page_config(layout="wide")

# Code um den Button-Design anzupassen
m = st.markdown("""
<style>
div.stButton > button:first-child {
    background-color: #ce1126;
    color: white;
    height: 3em;
    width: 14em;
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

# === Variablesm session state ====#

if 'checkWeather' not in st.session_state:
    st.session_state.checkWeather = False

########################################


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


_ = """
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

st.header("Historical Weather Data")
st.info("Source: https://meteostat.net ")
today = date.today()
last_year = today - timedelta(days=365 * 5)
# st.write("last_year: ", last_year)


# Import the required library
from geopy.geocoders import Nominatim

# Initialize Nominatim API
geolocator = Nominatim(user_agent="MyApp")

st.write("")
Ortseingabe = st.text_input("Enter location:", value=nearestWeatherstation)
st.write("")

location = geolocator.geocode(Ortseingabe)

from meteostat import Stations

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

    st.write("Nearest Weather Station: ", weatherstation_data)

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

st.subheader("")
checkButton = st.toggle("Check weather data!")
st.subheader("")

if checkButton:
    st.session_state.checkWeather = True
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
    st.sidebar.write(today)
    st.sidebar.metric(label="Today's Max Temperature in  \n" + str(nearestWeatherstation), value=todayMaxText,
                      delta=todayMaxMinDiff.round(1))
    st.sidebar.metric(label="Today's Min Temperature", value=todayMinText)
    st.sidebar.metric(label="Today's Windspeed", value=todayWspdText)

    st.subheader("")
    st.subheader("Historical data for " + Ortseingabe)

    st.info("Nearest weatherstation: " + nearestWeatherstation)
    st.subheader("")

    data_YearAvg = data.groupby('Year').agg({'tavg': 'mean'})['tavg']

    data_YearMax = data.groupby('Year').agg({'tmax': 'max'})['tmax']

    data_YearMin = data.groupby('Year').agg({'tmin': 'min'})['tmin']

    data_YearWspd = data.groupby('Year').agg({'wspd': 'mean'})['wspd']

    data_YearWprcp = data.groupby('Year').agg({'prcp': 'mean'})['prcp']

    data_Yearsnow = data.groupby('Year').agg({'snow': 'mean'})['snow']

    st.info("Yearly Averages")

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

    # FORECASTING mit Prophet #################################
    if (len(data)) > 20:
        st.sidebar.subheader("")
        st.sidebar.divider()
        st.sidebar.subheader("")
        ProphetforecastStarten = st.sidebar.toggle("Forecast with Prophet", key="forecast")
        if ProphetforecastStarten:

            forecastHorizon = st.sidebar.slider("Forecastperiods", min_value=1, value=24)

            freqEingabe = st.sidebar.selectbox("Select the frequency of the forecast", ["D", "W", "M", "Q", "Y"],
                                               index=2)

            forecastValueListe = data.columns.to_list()
            # using pop(0) to perform removal of first item
            # forecastValueListe.pop(0)

            forecastVariable = st.sidebar.selectbox(
                'Value to forecast?', forecastValueListe)
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

            st.subheader("")

            st.title("Prophet Forecast of " + forecastVariable)

            st.info(
                "Prophet is a time series forecasting tool developed by Facebook that is widely used for predicting future values based on historical data. It is designed to handle data with strong seasonal patterns and missing values. Prophet employs an additive model that decomposes time series data into components such as trend, seasonality, and holidays, allowing for more accurate predictions. It incorporates customizable parameters to adjust the sensitivity to different patterns in the data")

            forecastDateExpander = st.expander("Tables with Forecast Data >>")
            with forecastDateExpander:
                st.write('Forecast Data:')
                # Display the forecast output
                st.write(Prohetforecast_df)
                st.write(Prohetforecast_df.describe())

            forecastYhatMax = Prohetforecast_df['yhat'].max() * 1.2

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
            average_Values_per_year = data_Prohetforecast_df.groupby('Year')['yhat', forecastVariable].mean()
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