import streamlit as st
import requests
import pandas as pd
import os
import plotly.express as px

# 1. 網頁基礎配置
st.set_page_config(page_title="2015-2024 F1 Overview", page_icon="🏎️", layout="wide")

# 2. CSS 樣式：專業極簡紅黑風格
st.markdown("""
    <style>
    .main { background-color: #15151e; }
    [data-testid="stMetric"] {
        background-color: #1f1f27;
        padding: 20px;
        border-radius: 4px;
        border-left: 4px solid #e10600;
        box-shadow: 0px 4px 12px rgba(0,0,0,0.4);
    }
    [data-testid="stSidebar"] {
        background-color: #1f1f27;
    }
    h1, h2, h3 {
        color: #ffffff;
        font-family: 'Titillium Web', sans-serif;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. 側邊欄配置
st.sidebar.image("https://logodownload.org/wp-content/uploads/2016/11/formula-1-logo-7.png", use_container_width=True)
st.sidebar.markdown("---")
year = st.sidebar.slider("Season Select", 2015, 2024, 2024)
st.sidebar.info(f"Viewing: {year} Season Summary")

# 4. 直接串接官方 API 邏輯
@st.cache_data(show_spinner=False)
def fetch_data(year):
    s_url = f"https://api.jolpi.ca/ergast/f1/{year}/driverStandings.json"
    c_url = f"https://api.jolpi.ca/ergast/f1/{year}/circuits.json"
    
    standings = []
    circuits = []
    
    try:
        # 抓取積分榜
        s_res = requests.get(s_url, timeout=10).json()
        s_list = s_res['MRData']['StandingsTable']['StandingsLists'][0]['DriverStandings']
        for item in s_list:
            standings.append({
                "Position": item['position'],
                "Driver": f"{item['Driver']['givenName']} {item['Driver']['familyName']}",
                "Nationality": item['Driver']['nationality'],
                "DOB": item['Driver']['dateOfBirth'],
                "Points": float(item['points']),
                "Team": item['Constructors'][0]['name']
            })
            
        # 抓取賽道地圖
        c_res = requests.get(c_url, timeout=10).json()
        c_list = c_res['MRData']['CircuitTable']['Circuits']
        for c in c_list:
            circuits.append({
                "name": c['circuitName'],
                "lat": float(c['Location']['lat']),
                "lon": float(c['Location']['long']),
                "locality": c['Location']['locality'],
                "country": c['Location']['country']
            })
    except:
        pass
    return pd.DataFrame(standings), pd.DataFrame(circuits)

df, df_circuits = fetch_data(year)

# 5. 冠軍 Profile 區塊
if not df.empty:
    champ = df.iloc[0]
    st.markdown(f"# {year} World Champion")
    
    col_img, col_info = st.columns([1, 2])
    
    with col_img:
        driver_name = champ['Driver']
        file_name = driver_name.replace(" ", "_")
        local_path = f"img/{file_name}.png"
        
        # 優先讀取本地 img/ 資料夾下的照片
        if os.path.exists(local_path):
            st.image(local_path, width=280)
        else:
            # 備用縮寫頭像
            st.image(f"https://api.dicebear.com/7.x/initials/svg?seed={driver_name}", width=200)
            
    with col_info:
        st.title(driver_name)
        m1, m2, m3 = st.columns(3)
        m1.metric("TEAM", champ['Team'])
        m2.metric("POINTS", f"{int(champ['Points'])} PTS")
        m3.metric("RANKING", f"P{int(champ['Position'])}")
        
        st.divider()
        
        inf1, inf2 = st.columns(2)
        b_year = champ['DOB'].split('-')[0] if 'DOB' in champ else "N/A"
        inf1.markdown(f"**Birth Year**  \n{b_year}")
        inf2.markdown(f"**Nationality**  \n{champ['Nationality']}")

st.divider()

# 6. 數據互動分頁
tab1, tab2 = st.tabs(["Standings", "Circuit Map"])

with tab1:
    if not df.empty:
        teams = sorted(df['Team'].unique())
        selected_teams = st.multiselect("Filter by Team:", teams, default=teams)
        filtered_df = df[df['Team'].isin(selected_teams)]
        
        st.dataframe(
            filtered_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Points": st.column_config.ProgressColumn("Score Progress", format="%.0f", min_value=0, max_value=int(df['Points'].max())),
                "Position": "POS", "Driver": "Driver", "Nationality": "NAT", "Team": "Team"
            }
        )

with tab2:
    if not df_circuits.empty:
        # Plotly 深色地圖
        fig = px.scatter_mapbox(
            df_circuits, lat="lat", lon="lon", hover_name="name",
            hover_data=["locality", "country"], zoom=1, height=500
        )
        fig.update_layout(
            mapbox_style="carto-darkmatter",
            margin={"r":0,"t":0,"l":0,"b":0},
            paper_bgcolor="#15151e"
        )
        fig.update_traces(marker=dict(size=12, color="#e10600"))
        st.plotly_chart(fig, use_container_width=True)
        
        st.dataframe(df_circuits[['name', 'locality', 'country']], use_container_width=True, hide_index=True)