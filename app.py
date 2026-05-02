import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime

# 1. 頁面基本設定
st.set_page_config(page_title="F1 DATA HUB", layout="wide")

# 2. 數據抓取函數
@st.cache_data(show_spinner="Fetching standings...")
def get_driver_standings(year):
    url = f"https://api.jolpi.ca/ergast/f1/{year}/driverstandings.json"
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, timeout=10, headers=headers)
        response.raise_for_status()
        data = response.json()
        standings = data['MRData']['StandingsTable']['StandingsLists'][0]['DriverStandings']
        
        processed_data = []
        for item in standings:
            driver = item['Driver']
            processed_data.append({
                "Rank": int(item['position']),
                "Driver": f"{driver['givenName']} {driver['familyName']}",
                "Nationality": driver['nationality'],
                "DOB": driver['dateOfBirth'],
                "Constructor": item['Constructors'][0]['name'],
                "Points": float(item['points']),
                "Wins": int(item['wins']),
                "DriverID": driver['driverId']
            })
        return pd.DataFrame(processed_data)
    except Exception:
        return None

@st.cache_data(show_spinner="Loading all GP results...")
def get_race_results(year):
    # 使用 limit=1000 確保獲取全年所有比賽
    url = f"https://api.jolpi.ca/ergast/f1/{year}/results.json?limit=1000"
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, timeout=10, headers=headers)
        response.raise_for_status()
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
                "P1": p1, "P2": p2, "P3": p3,
                "lat": float(r['Circuit']['Location']['lat']),
                "lon": float(r['Circuit']['Location']['long'])
            })
        return pd.DataFrame(schedule_data)
    except Exception:
        return None

# 3. 側邊欄 UI
st.sidebar.title("F1 CONTROL CENTER")
selected_year = st.sidebar.selectbox("SEASON", list(range(2024, 2014, -1)))
st.sidebar.markdown("---")
nav_option = st.sidebar.radio("NAVIGATION", ["SEASON OVERVIEW", "RACE RESULTS"])

# 4. 數據獲取
df_drivers = get_driver_standings(selected_year)
df_races = get_race_results(selected_year)

# 5. 頁面邏輯
if df_drivers is None or df_races is None:
    st.error("DATABASE CONNECTION ERROR: The API domain might be updating. Please try again later.")
else:
    if nav_option == "SEASON OVERVIEW":
        st.title(f"{selected_year} SEASON OVERVIEW")
        
        # 冠軍區域
        champ = df_drivers.iloc[0]
        col1, col2 = st.columns([1, 2])
        
        with col1:
            # 確保 DriverID 格式正確 (例如 lewis_hamilton.png)
            img_id = champ['DriverID'].replace('-', '_')
            img_path = f"img/{img_id}.png"
            try:
                st.image(img_path, use_container_width=True)
            except:
                st.info(f"Photo of {champ['Driver']} not found in /img folder.")

        with col2:
            st.caption("WORLD CHAMPION")
            st.header(champ['Driver'].upper())
            
            # 顯示國籍與出生年份
            birth_year = datetime.strptime(champ['DOB'], '%Y-%m-%d').year
            st.subheader(f"🏁 {champ['Nationality']} | 🎂 Born {birth_year}")
            
            m1, m2 = st.columns(2)
            m1.metric("POINTS", f"{champ['Points']} PTS")
            m2.metric("WINS", f"{champ['Wins']} WINS")
            st.write(f"**CONSTRUCTOR:** {champ['Constructor']}")
            st.progress(1.0)

        st.markdown("---")
        c_left, c_right = st.columns([1, 1])
        with c_left:
            st.subheader("DRIVER STANDINGS")
            # 顯示更多資訊
            st.dataframe(df_drivers[['Rank', 'Driver', 'Constructor', 'Points', 'Nationality']], 
                         hide_index=True, use_container_width=True)
        with c_right:
            st.subheader("CIRCUIT LOCATIONS")
            fig = px.scatter_mapbox(df_races, lat="lat", lon="lon", hover_name="Grand Prix",
                                    zoom=0.5, height=400)
            fig.update_layout(mapbox_style="carto-darkmatter", margin={"r":0,"t":0,"l":0,"b":0})
            st.plotly_chart(fig, use_container_width=True)

    elif nav_option == "RACE RESULTS":
        st.title(f"{selected_year} CALENDAR & RESULTS")
        # 統計欄位
        m1, m2, m3 = st.columns(3)
        m1.metric("TOTAL ROUNDS", len(df_races))
        m2.metric("UNIQUE WINNERS", df_races['P1'].nunique())
        m3.metric("STATUS", "OFFICIAL")
        
        st.markdown("---")
        st.dataframe(df_races[['Round', 'Grand Prix', 'Date', 'P1', 'P2', 'P3']],
                     use_container_width=True, hide_index=True)

# 6. CSS 高級定制 (標題列紅底白字)
st.markdown("""
    <style>
    /* 全域風格 */
    .stApp { background-color: #15151e; color: #ffffff; }
    [data-testid="stSidebar"] { background-color: #1f1f27; }
    [data-testid="stMetricValue"] { color: #e10600 !important; font-family: 'Courier New', monospace; }
    
    /* 強制修改 Dataframe 標題列樣式 (紅底白字) */
    .stDataFrame thead tr th {
        background-color: #e10600 !important;
        color: white !important;
        font-weight: bold !important;
        text-transform: uppercase;
    }
    
    /* 調整表格內文字 */
    .stDataFrame td { font-size: 14px; }
    </style>
    """, unsafe_allow_html=True)
