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
    # 第一步：抓取全年度賽程清單
    schedule_url = f"https://api.jolpi.ca/ergast/f1/{year}.json?limit=1000"
    # 第二步：僅抓取分站冠軍 (results/1.json)
    results_url = f"https://api.jolpi.ca/ergast/f1/{year}/results/1.json?limit=1000"
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        sched_res = requests.get(schedule_url, timeout=10, headers=headers).json()
        all_races = sched_res['MRData']['RaceTable']['Races']
        
        res_res = requests.get(results_url, timeout=10, headers=headers).json()
        results_data = res_res['MRData']['RaceTable']['Races']
        winner_map = {r['round']: r['Results'][0]['Driver']['familyName'] for r in results_data if r.get('Results')}
        
        final_schedule = []
        for r in all_races:
            rnd = r['round']
            winner = winner_map.get(rnd, "TBC")
            
            final_schedule.append({
                "Round": int(rnd),
                "Grand Prix": r['raceName'].replace("Grand Prix", "GP"),
                "Date": r['date'],
                "Winner": winner,
                "lat": float(r['Circuit']['Location']['lat']),
                "long": float(r['Circuit']['Location']['long'])
            })
        return pd.DataFrame(final_schedule)
    except Exception:
        return None

# 3. 側邊欄 UI
# 解決鋸齒狀並對齊寬度：使用 CSS 注入
st.sidebar.markdown(
    """
    <div style="text-align: left;">
        <img src="https://upload.wikimedia.org/wikipedia/commons/3/33/F1.svg" 
             style="width: 100%; max-width: 250px; image-rendering: -webkit-optimize-contrast; margin-bottom: 20px;">
    </div>
    """, 
    unsafe_allow_html=True
)

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
            # 照片匹配邏輯：Title_Case (例如 Lewis_Hamilton.png)
            name_parts = champ['DriverID'].replace('-', '_').split('_')
            formatted_id = "_".join([p.capitalize() for p in name_parts])
            img_path = f"img/{formatted_id}.png"
            
            try:
                st.image(img_path, use_container_width=True)
            except:
                st.caption(f"IMAGE: {champ['Driver'].upper()}")

        with col2:
            st.caption("SEASON CHAMPION")
            st.header(champ['Driver'].upper())
            birth_year = datetime.strptime(champ['DOB'], '%Y-%m-%d').year
            st.markdown(f"**{champ['Nationality']}** | BORN {birth_year}")
            
            m1, m2 = st.columns(2)
            # 純數字顯示
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
        valid_winners = df_races[df_races['Winner'] != 'TBC']['Winner'].nunique()
        m2.metric("WINNERS", valid_winners)
        # 修改：Status 改為 COMPLETED
        m3.metric("STATUS", "COMPLETED")
        
        st.markdown("---")
        st.dataframe(df_races[['Round', 'Grand Prix', 'Date', 'Winner']],
                     use_container_width=True, hide_index=True)

# 6. CSS 高級定制
st.markdown("""
    <style>
    .stApp { background-color: #15151e; color: #ffffff; }
    [data-testid="stSidebar"] { background-color: #1f1f27; }
    [data-testid="stMetricValue"] { color: #e10600 !important; font-family: 'Courier New', monospace; }
    
    /* 表格標頭：紅底白字 */
    .stDataFrame thead tr th {
        background-color: #e10600 !important;
        color: white !important;
        font-weight: bold !important;
    }
    
    .stDataFrame td { font-size: 14px; }
    .block-container { padding-top: 2rem; }
    </style>
    """, unsafe_allow_html=True)
