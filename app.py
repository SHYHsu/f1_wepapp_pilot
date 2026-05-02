import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime

# 1. 頁面基本設定
st.set_page_config(page_title="F1 DATA HUB", layout="wide")

# 2. 數據抓取函數
@st.cache_data(show_spinner=False)
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
                "Nationality": driver['nationality'].upper(),
                "DOB": driver['dateOfBirth'],
                "Constructor": item['Constructors'][0]['name'],
                "Points": int(float(item['points'])), 
                "Wins": int(item['wins']),
                "DriverID": driver['driverId']
            })
        return pd.DataFrame(processed_data)
    except Exception:
        return None

@st.cache_data(show_spinner=False)
def get_race_results(year):
    # 第一步：抓取全年度的賽程清單 (確保所有 GP 都出現)
    schedule_url = f"https://api.jolpi.ca/ergast/f1/{year}.json?limit=1000"
    # 第二步：抓取目前的比賽結果
    results_url = f"https://api.jolpi.ca/ergast/f1/{year}/results.json?limit=1000"
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        # 獲取完整賽程
        sched_res = requests.get(schedule_url, timeout=10, headers=headers).json()
        all_races = sched_res['MRData']['RaceTable']['Races']
        
        # 獲取已有的結果
        res_res = requests.get(results_url, timeout=10, headers=headers).json()
        results_data = res_res['MRData']['RaceTable']['Races']
        # 建立一個 round 到 results 的對照表
        results_map = {r['round']: r['Results'] for r in results_data}
        
        final_schedule = []
        for r in all_races:
            rnd = r['round']
            res_list = results_map.get(rnd, [])
            
            p1 = res_list[0]['Driver']['familyName'] if len(res_list) > 0 else "TBC"
            p2 = res_list[1]['Driver']['familyName'] if len(res_list) > 1 else "TBC"
            p3 = res_list[2]['Driver']['familyName'] if len(res_list) > 2 else "TBC"
            
            final_schedule.append({
                "Round": int(rnd),
                "Grand Prix": r['raceName'].replace("Grand Prix", "GP"),
                "Date": r['date'],
                "P1": p1, "P2": p2, "P3": p3,
                "lat": float(r['Circuit']['Location']['lat']),
                "lon": float(r['Circuit']['Location']['long'])
            })
        return pd.DataFrame(final_schedule)
    except Exception:
        return None

# 3. 側邊欄 UI
# 修正 F1 商標：使用與截圖一致的官方紅標 URL (穩定連結)
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/3/33/F1.svg/1024px-F1.svg.png", width=150)
st.sidebar.title("CONTROL CENTER")
selected_year = st.sidebar.selectbox("SEASON", list(range(2024, 2014, -1)))
st.sidebar.markdown("---")
nav_option = st.sidebar.radio("NAVIGATION", ["SEASON OVERVIEW", "RACE RESULTS"])

# 4. 數據獲取
df_drivers = get_driver_standings(selected_year)
df_races = get_race_results(selected_year)

# 5. 頁面邏輯
if df_drivers is None or df_races is None:
    st.error("DATABASE CONNECTION ERROR: Please refresh or select another year.")
else:
    if nav_option == "SEASON OVERVIEW":
        st.title(f"{selected_year} SEASON OVERVIEW")
        champ = df_drivers.iloc[0]
        col1, col2 = st.columns([1, 2])
        
        with col1:
            # 修正：精確對應 Lewis_Hamilton.png 格式 (Title_Case)
            parts = champ['DriverID'].replace('-', '_').split('_')
            formatted_id = "_".join([p.capitalize() for p in parts])
            img_path = f"img/{formatted_id}.png"
            
            try:
                st.image(img_path, use_container_width=True)
            except:
                st.info(f"PHOTO: {champ['Driver'].upper()}")

        with col2:
            st.caption("SEASON CHAMPION")
            st.header(champ['Driver'].upper())
            birth_year = datetime.strptime(champ['DOB'], '%Y-%m-%d').year
            st.markdown(f"**{champ['Nationality']}** | BORN {birth_year}")
            
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
            fig = px.scatter_mapbox(df_races, lat="lat", lon="lon", hover_name="Grand Prix",
                                    zoom=0.5, height=400)
            fig.update_layout(mapbox_style="carto-darkmatter", margin={"r":0,"t":0,"l":0,"b":0})
            st.plotly_chart(fig, use_container_width=True)

    elif nav_option == "RACE RESULTS":
        st.title(f"{selected_year} CALENDAR & RESULTS")
        m1, m2, m3 = st.columns(3)
        m1.metric("ROUNDS", len(df_races))
        valid_winners = df_races[df_races['P1'] != 'TBC']['P1'].nunique()
        m2.metric("WINNERS", valid_winners)
        m3.metric("STATUS", "OFFICIAL")
        
        st.markdown("---")
        st.dataframe(df_races[['Round', 'Grand Prix', 'Date', 'P1', 'P2', 'P3']],
                     use_container_width=True, hide_index=True)

# 6. CSS (標題列紅底白字)
st.markdown("""
    <style>
    .stApp { background-color: #15151e; color: #ffffff; }
    [data-testid="stSidebar"] { background-color: #1f1f27; }
    [data-testid="stMetricValue"] { color: #e10600 !important; font-family: 'Courier New', monospace; }
    .stDataFrame thead tr th {
        background-color: #e10600 !important;
        color: white !important;
        font-weight: bold !important;
    }
    .stDataFrame td { font-size: 14px; }
    .block-container { padding-top: 2rem; }
    </style>
    """, unsafe_allow_html=True)
