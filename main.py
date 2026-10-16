import os
import requests
from datetime import datetime, timedelta

# 1. 讀取隱私環境變數
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
SERPAPI_KEY = os.getenv("SERPAPI_KEY")

def get_multi_airline_prices():
    origin = "TPE"         # 出發地：台北
    destination = "TYO"    # 目的地：東京 (含羽田/成田)

    # 🗓️ 動態日期設定：自動推遲至 60 天後出發，玩 5 天
    today = datetime.now()
    DAYS_UNTIL_DEPART = 60
    TRIP_DURATION = 5

    outbound_dt = today + timedelta(days=DAYS_UNTIL_DEPART)
    return_dt = outbound_dt + timedelta(days=TRIP_DURATION)

    outbound_date = outbound_dt.strftime("%Y-%m-%d")
    return_date = return_dt.strftime("%Y-%m-%d")

    # 2. 呼叫 Google Flights API (SerpApi)
    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google_flights",
        "departure_id": origin,
        "arrival_id": destination,
        "outbound_date": outbound_date,
        "return_date": return_date,
        "currency": "TWD",
        "hl": "zh-TW",
        "api_key": SERPAPI_KEY
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        all_flights = data.get("best_flights", []) + data.get("other_flights", [])
        if not all_flights:
            print(f"未找到 {outbound_date} 至 {return_date} 的航班")
            return

        # 3. 整理每家航空公司的最低價格
        airline_best_prices = {}
        for flight in all_flights:
            price = flight.get("price")
            flight_info = flight.get("flights", [])[0]
            airline_name = flight_info.get("airline", "未知航空")
            
            if airline_name not in airline_best_prices or price < airline_best_prices[airline_name]:
                airline_best_prices[airline_name] = price

        # 4. 組成 Discord 卡片訊息
        msg = f"✈️ **【機票動態比價】{origin} ➡️ {destination} 各家航空價格**\n"
        msg += f"📅 監控日期：`{outbound_date}` ～ `{return_date}` (往後推 60 天)\n"
        msg += "-----------------------------------\n"

        sorted_prices = sorted(airline_best_prices.items(), key=lambda x: x[1])
        for airline, price in sorted_prices:
            msg += f"🔹 **{airline}**：NT$ **{price:,}**\n"

        msg += "-----------------------------------\n"
        msg += f"💡 *資料來源：Google Flights*"

        print(msg)
        send_discord_notification(msg)

    except Exception as e:
        print(f"抓取機票失敗: {e}")

def send_discord_notification(message):
    if not DISCORD_WEBHOOK:
        print("❌ 未設定 DISCORD_WEBHOOK！")
        return
    payload = {"content": message}
    requests.post(DISCORD_WEBHOOK, json=payload)

if __name__ == "__main__":
    get_multi_airline_prices()
