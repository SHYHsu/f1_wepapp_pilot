import streamlit as st
import pandas as pd
import requests
import plotly.express as px

# 1. 頁面基本設定
st.set_page_config(page_title="F1 DATA HUB", layout="wide")

# 2. 數據抓取函數 (更新為 api.jolpi.ca 新網址)
@st.cache_data(show_spinner="Fetching data from API...")
def get_driver_standings(year):
    # 新網域路徑，且 driverstandings 改為全小寫
    url = f"https://api.jolpi.ca/ergast/f1/{year}/driverstandings.json"
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, timeout=10, headers=headers)
        response.raise_for_status()
        data = response.json()
        # 解析路徑保持一致
        standings = data['MRData']['StandingsTable']['StandingsLists'][0]['DriverStandings']
        
        processed_data = []
        for item in standings:
            processed_data.append({
                "Rank": int(item['position']),
                "Driver": f"{item['Driver']['givenName']} {item['Driver']['familyName']}",
                "Constructor": item['Constructors'][0]['name'],
                "Points": float(item['points']),
                "Wins": int(item['wins']),
                "DriverID": item['Driver']['driverId']
            })
        return pd.DataFrame(processed_data)
    except Exception as e:
        return None

@st.cache_data(show_spinner="Loading race results...")
def get_race_results(year):
    # 更新為新網域路徑
    url = f"https://api.jolpi.ca/ergast/f1/{year}/results.json?limit=1000"
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
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
                "lon": float(r['Circuit']['Location']['long']),
                "Loc": r['Circuit']['Location']['locality']
            })
        return pd.DataFrame(schedule_data)
    except Exception as e:
        return None

# 3. 側邊欄 UI
st.sidebar.title("F1 CONTROL CENTER")
selected_year = st.sidebar.selectbox("SEASON", list(range(2024, 2014, -1)))
st.sidebar.markdown("---")
nav_option = st.sidebar.radio("NAVIGATION", ["SEASON OVERVIEW", "RACE RESULTS"])

# 4. 數據抓取
df_drivers = get_driver_standings(selected_year)
df_races = get_race_results(selected_year)

# 5. 頁面邏輯
if df_drivers is None or df_races is None:
    st.error("DATABASE CONNECTION ERROR: Please refresh the page or try again later.")
    st.info("The F1 API server might be temporarily unavailable or domain has changed.")
else:
    if nav_option == "SEASON OVERVIEW":
        st.title(f"{selected_year} SEASON OVERVIEW")
        
        # 年度冠軍精選
        champ = df_drivers.iloc[0]
        col1, col2 = st.columns([1, 2])
        with col1:
            # 處理 DriverID 中的連字號以匹配圖片檔名
            img_path = f"img/{champ['DriverID'].replace('-', '_')}.png"
            try:
                st.image(img_path, use_container_width=True)
            except:
                st.caption(f"IMAGE NOT FOUND: {champ['Driver']}")
        with col2:
            st.caption("WORLD CHAMPION")
            st.header(champ['Driver'].upper())
            st.metric("TOTAL POINTS", f"{champ['Points']} PTS")
            st.write(f"**CONSTRUCTOR:** {champ['Constructor']}")
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
                                    zoom=0.5, height=400)
            fig.update_layout(mapbox_style="carto-darkmatter", margin={"r":0,"t":0,"l":0,"b":0})
            st.plotly_chart(fig, use_container_width=True)

    elif nav_option == "RACE RESULTS":
        st.title(f"{selected_year} CALENDAR & RESULTS")
        m1, m2, m3 = st.columns(3)
        m1.metric("TOTAL ROUNDS", len(df_races))
        m2.metric("UNIQUE WINNERS", df_races['P1'].nunique())
        m3.metric("STATUS", "COMPLETED")
        
        st.markdown("---")
        st.subheader("PODIUM FINISHERS")
        st.dataframe(df_races[['Round', 'Grand Prix', 'Date', 'P1', 'P2', 'P3']],
                     use_container_width=True, hide_index=True)

# 6. CSS 視覺優化
st.markdown("""
    <style>
    .stApp { background-color: #15151e; color: #ffffff; }
    [data-testid="stMetricValue"] { color: #e10600 !important; font-family: monospace; }
    [data-testid="stSidebar"] { background-color: #1f1f27; }
    /* 表格標頭紅色風格 */
    thead tr th { 
        background-color: #e10600 !important; 
        color: white !important; 
    }
    </style>
    """, unsafe_allow_html=True)
