# --- 1. 數據抓取函數 (加入防護機制) ---
@st.cache_data
def get_driver_standings(year):
    url = f"https://jolpica.net/api/f1/{year}/driverStandings.json"
    try:
        # 設定 timeout=10 秒，避免網頁卡死
        response = requests.get(url, timeout=10)
        response.raise_for_status() # 檢查是否成功連線
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
                "DriverID": item['Driver']['driverId']
            })
        return pd.DataFrame(processed_data)
    except Exception as e:
        st.error(f"無法從 API 獲取積分數據，請稍後再試。")
        return pd.DataFrame() # 回傳空表格避免後續程式出錯

@st.cache_data
def get_race_results(year):
    url = f"https://jolpica.net/api/f1/{year}/results.json?limit=1000"
    try:
        response = requests.get(url, timeout=10)
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
        st.error(f"無法從 API 獲取賽程數據。")
        return pd.DataFrame()
