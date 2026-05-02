import streamlit as st
import pandas as pd
import requests
import plotly.express as px

# 頁面基本設定
st.set_page_config(page_title="F1 Data Hub 2015-2024", layout="wide")

# --- 1. 數據抓取函數 ---
@st.cache_data
def get_driver_standings(year):
    url = f"https://jolpica.net/api/f1/{year}/driverStandings.json"
    response = requests.get(url)
    data = response.json()
    standings = data['MRData']['StandingsTable']['StandingsLists'][0]['DriverStandings']
    
    processed_data = []
    for item in standings:
        processed_data.append({
            "Rank": int(item['position']),
            "Driver": f"{item['Driver']['givenName']} {item['Driver']['familyName']}",
            "Constructor": item['Constructors'][0]['name'],
            "Points": float(item['points']),
            "Wins": int(item['wins']),
            "Nationality": item['Driver']['nationality'],
            "DOB": item['Driver']['dateOfBirth'],
            "DriverID": item['Driver']['driverId']
        })
    return pd.DataFrame(processed_data)

@st.cache_data
def get_race_results(year):
    url = f"https://jolpica.net/api/f1/{year}/results.json?limit=1000"
    response = requests.get(url)
    data = response.json()
    races = data['MRData']['RaceTable']['Races']
    
    schedule_data = []
    for r in races:
        results = r['Results'][:3]
        p1 = results[0]['Driver']['familyName'] if len(results) > 0 else "-"
        p2 = results[1]['Driver']['familyName'] if len(results) > 1 else "-"
        p3 = results[2]['Driver']['familyName'] if len(results) > 2 else "-"
        
        schedule_data.append({
            "Round": int(r['round']),
            "Grand Prix": r['raceName'].replace("Grand Prix", "GP"),
            "Date": r['date'],
            "P1": p1,
            "P2": p2,
            "P3": p3,
            "lat": float(r['Circuit']['Location']['lat']),
            "lon": float(r['Circuit']['Location']['long']),
            "Loc": r['Circuit']['Location']['locality']
        })
    return pd.DataFrame(schedule_data)

# --- 2. 側邊欄設定 ---
st.sidebar.title("F1 CONTROL CENTER")
selected_year = st.sidebar.selectbox("SEASON", list(range(2024, 2014, -1)))
st.sidebar.markdown("---")
nav_option = st.sidebar.radio("NAVIGATION", ["SEASON OVERVIEW", "RACE RESULTS"])

# 預先抓取數據
df_drivers = get_driver_standings(selected_year)
df_races = get_race_results(selected_year)

# --- 3. 頁面邏輯：年度總覽 ---
if nav_option == "SEASON OVERVIEW":
    st.title(f"{selected_year} SEASON OVERVIEW")
    
    champ = df_drivers.iloc[0]
    col1, col2 = st.columns([1, 2])
    
    with col1:
        img_path = f"img/{champ['DriverID'].replace('-', '_')}.png"
        try:
            st.image(img_path, use_container_width=True)
        except:
            st.info(f"Image for {champ['Driver']} not found")
            
    with col2:
        st.caption("WORLD CHAMPION")
        st.header(champ['Driver'].upper())
        st.metric("TOTAL POINTS", f"{champ['Points']} PTS")
        st.write(f"**CONSTRUCTOR:** {champ['Constructor']}")
        st.write(f"**NATIONALITY:** {champ['Nationality']}")
        st.progress(1.0)

    st.markdown("---")
    
    c_left, c_right = st.columns([1, 1])
    with c_left:
        st.subheader("DRIVER STANDINGS")
        st.dataframe(df_drivers[['Rank', 'Driver', 'Constructor', 'Points', 'Wins']], 
                     hide_index=True, use_container_width=True)
    
    with c_right:
        st.subheader("CIRCUIT LOCATIONS")
        fig = px.scatter_mapbox(df_races, lat="lat", lon="lon", hover_name="Grand Prix",
                                hover_data=["Loc", "Date"], zoom=0.5, height=400)
        fig.update_layout(mapbox_style="carto-darkmatter", margin={"r":0,"t":0,"l":0,"b":0})
        st.plotly_chart(fig, use_container_width=True)

# --- 4. 頁面邏輯：分站賽程與成績 ---
elif nav_option == "RACE RESULTS":
    st.title(f"{selected_year} CALENDAR & RESULTS")
    
    total_races = len(df_races)
    unique_winners = df_races['P1'].nunique()
    
    m1, m2, m3 = st.columns(3)
    m1.metric("TOTAL ROUNDS", f"{total_races}")
    m2.metric("UNIQUE WINNERS", f"{unique_winners}")
    m3.metric("STATUS", "COMPLETED")

    st.markdown("---")
    
    st.subheader("PODIUM FINISHERS BY ROUND")
    st.dataframe(
        df_races[['Round', 'Grand Prix', 'Date', 'P1', 'P2', 'P3']],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Round": st.column_config.NumberColumn("RD"),
            "Date": st.column_config.DateColumn("DATE"),
            "P1": "WINNER",
            "P2": "SECOND",
            "P3": "THIRD"
        }
    )
    st.caption(f"Source: Jolpica/Ergast F1 API | Last Data: {df_races.iloc[-1]['Date']}")

# --- 5. 強制俐落配色 CSS ---
st.markdown("""
    <style>
    .stApp { background-color: #15151e; color: #ffffff; }
    [data-testid="stMetricValue"] { color: #e10600 !important; font-family: monospace; }
    [data-testid="stSidebar"] { background-color: #1f1f27; }
    .stDataFrame { border: 1px solid #38383f; }
    h1, h2, h3 { letter-spacing: -0.5px; }
    </style>
    """, unsafe_allow_html=True)
