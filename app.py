import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime
import os

st.set_page_config(page_title="F1 DATA HUB", layout="wide")

# 數據抓取函數
@st.cache_data(show_spinner=False)
def get_driver_standings(year):
    url = f"https://api.jolpi.ca/ergast/f1/{year}/driverstandings.json"
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, timeout=5, headers=headers)
        response.raise_for_status()
        data = response.json()
        standings = data['MRData']['StandingsTable']['StandingsLists'][0]['DriverStandings']
        
        processed_data = []
        for item in standings:
            driver = item['Driver']
            processed_data.append({
                "Rank": int(item['position']),
                "Driver": f"{driver['givenName']} {driver['familyName']}",
                "Nationality": driver['nationality'].upper(),
                "DOB": driver['dateOfBirth'],
                "Constructor": item['Constructors'][0]['name'],
                "Points": int(float(item['points'])), 
                "Wins": int(item['wins']),
                "DriverID": driver['driverId']
            })
        df = pd.DataFrame(processed_data)
        # 自動存檔備份：確保 data 資料夾存在
        if not os.path.exists("data"): os.makedirs("data")
        df.to_csv(f"data/standings_{year}.csv", index=False)
        return df, "LIVE"
    except Exception:
        fallback_path = f"data/standings_{year}.csv"
        if os.path.exists(fallback_path):
            return pd.read_csv(fallback_path), "OFFLINE"
        return None, "ERROR"

@st.cache_data(show_spinner=False)
def get_race_results(year):
    schedule_url = f"https://api.jolpi.ca/ergast/f1/{year}.json?limit=1000"
    results_url = f"https://api.jolpi.ca/ergast/f1/{year}/results/1.json?limit=1000"
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        sched_res = requests.get(schedule_url, timeout=5, headers=headers).json()
        all_races = sched_res['MRData']['RaceTable']['Races']
        res_res = requests.get(results_url, timeout=5, headers=headers).json()
        results_data = res_res['MRData']['RaceTable']['Races']
        winner_map = {r['round']: r['Results'][0]['Driver']['familyName'] for r in results_data if r.get('Results')}
        
        final_schedule = []
        for r in all_races:
            rnd = r['round']
            final_schedule.append({
                "Round": int(rnd), "Grand Prix": r['raceName'].replace("Grand Prix", "GP"),
                "Date": r['date'], "Winner": winner_map.get(rnd, "TBC"),
                "lat": float(r['Circuit']['Location']['lat']), "long": float(r['Circuit']['Location']['long'])
            })
        df = pd.DataFrame(final_schedule)
        # 自動存檔備份
        if not os.path.exists("data"): os.makedirs("data")
        df.to_csv(f"data/results_{year}.csv", index=False)
        return df, "LIVE"
    except Exception:
        fallback_path = f"data/results_{year}.csv"
        if os.path.exists(fallback_path):
            return pd.read_csv(fallback_path), "OFFLINE"
        return None, "ERROR"

# 側邊欄
st.sidebar.markdown(
    """<div style="text-align: left;"><img src="https://upload.wikimedia.org/wikipedia/commons/3/33/F1.svg" 
    style="width: 100%; max-width: 250px; image-rendering: -webkit-optimize-contrast; margin-bottom: 20px;"></div>""", 
    unsafe_allow_html=True)
st.sidebar.title("CONTROL CENTER")
selected_year = st.sidebar.selectbox("SEASON", list(range(2024, 2014, -1)))
st.sidebar.markdown("---")
nav_option = st.sidebar.radio("NAVIGATION", ["SEASON OVERVIEW", "RACE RESULTS"])

df_drivers, d_status = get_driver_standings(selected_year)
df_races, r_status = get_race_results(selected_year)

if df_drivers is None or df_races is None:
    st.error("DATABASE CONNECTION ERROR: No live data or local backup found.")
else:
    if d_status == "OFFLINE":
        st.warning(f"⚠️ OFFLINE MODE: Showing cached data for {selected_year}.")

    if nav_option == "SEASON OVERVIEW":
        st.title(f"{selected_year} SEASON OVERVIEW")
        champ = df_drivers.iloc[0]
        col1, col2 = st.columns([1, 2])
        
        with col1:
            # 針對 Lewis_Hamilton.png 與 Nico_Rosberg.png 的精確匹配
            d_id = champ['DriverID']
            # 將 ID (如 lewis_hamilton) 轉為 Title_Case (Lewis_Hamilton)
            formatted_name = "_".join([p.capitalize() for p in d_id.replace('-', '_').split('_')])
            
            img_path = f"img/{formatted_name}.png"
            if os.path.exists(img_path):
                st.image(img_path, use_container_width=True)
            else:
                st.info(f"PHOTO: {champ['Driver'].upper()}")

        with col2:
            st.caption("SEASON CHAMPION")
            st.header(champ['Driver'].upper())
            try:
                birth_year = datetime.strptime(str(champ['DOB']), '%Y-%m-%d').year
                st.markdown(f"**{champ['Nationality']}** | BORN {birth_year}")
            except:
                st.markdown(f"**{champ['Nationality']}**")
            m1, m2 = st.columns(2)
            m1.metric("POINTS", champ['Points'])
            m2.metric("WINS", champ['Wins'])
            st.write(f"**CONSTRUCTOR:** {champ['Constructor']}")
            st.progress(1.0)

        st.markdown("---")
        c_left, c_right = st.columns([1, 1])
        with c_left:
            st.subheader("DRIVER STANDINGS")
            st.dataframe(df_drivers[['Rank', 'Driver', 'Constructor', 'Points', 'Nationality']], 
                         hide_index=True, use_container_width=True)
        with c_right:
            st.subheader("CIRCUIT LOCATIONS")
            fig = px.scatter_mapbox(df_races, lat="lat", lon="long", hover_name="Grand Prix",
                                    zoom=0.5, height=400)
            fig.update_layout(mapbox_style="carto-darkmatter", margin={"r":0,"t":0,"l":0,"b":0})
            st.plotly_chart(fig, use_container_width=True)

    elif nav_option == "RACE RESULTS":
        st.title(f"{selected_year} CALENDAR & RESULTS")
        m1, m2, m3 = st.columns(3)
        m1.metric("ROUNDS", len(df_races))
        m2.metric("WINNERS", df_races[df_races['Winner'] != 'TBC']['Winner'].nunique())
        m3.metric("STATUS", "COMPLETED")
        st.markdown("---")
        st.dataframe(df_races[['Round', 'Grand Prix', 'Date', 'Winner']],
                     use_container_width=True, hide_index=True)

st.markdown("""<style>
    .stApp { background-color: #15151e; color: #ffffff; }
    [data-testid="stSidebar"] { background-color: #1f1f27; }
    [data-testid="stMetricValue"] { color: #e10600 !important; font-family: 'Courier New', monospace; }
    .stDataFrame thead tr th { background-color: #e10600 !important; color: white !important; font-weight: bold !important; }
    .stDataFrame td { font-size: 14px; }
    .block-container { padding-top: 2rem; }
    </style>""", unsafe_allow_html=True)
