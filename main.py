import os
import asyncio
import requests
from datetime import datetime, timedelta
import discord

# 1. 讀取 GitHub Secrets 環境變數
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID")
SERPAPI_KEY = os.getenv("SERPAPI_KEY")

def fetch_flight_data():
    origin = "TPE"
    destination = "TYO"

    today = datetime.now()
    DAYS_UNTIL_DEPART = 60
    TRIP_DURATION = 5

    outbound_dt = today + timedelta(days=DAYS_UNTIL_DEPART)
    return_dt = outbound_dt + timedelta(days=TRIP_DURATION)

    outbound_date = outbound_dt.strftime("%Y-%m-%d")
    return_date = return_dt.strftime("%Y-%m-%d")

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
            return None

        airline_best_prices = {}
        for flight in all_flights:
            price = flight.get("price")
            flight_info = flight.get("flights", [])[0]
            airline_name = flight_info.get("airline", "未知航空")
            
            if airline_name not in airline_best_prices or price < airline_best_prices[airline_name]:
                airline_best_prices[airline_name] = price

        msg = f"✈️ **【機票動態比價】{origin} ➡️ {destination} 各家航空價格**\n"
        msg += f"📅 監控日期：`{outbound_date}` ～ `{return_date}` (往後推 60 天)\n"
        msg += "-----------------------------------\n"

        sorted_prices = sorted(airline_best_prices.items(), key=lambda x: x[1])
        for airline, price in sorted_prices:
            msg += f"🔹 **{airline}**：NT$ **{price:,}**\n"

        msg += "-----------------------------------\n"
        msg += f"💡 *資料來源：Google Flights*"

        return msg
    except Exception as e:
        print(f"抓取失敗: {e}")
        return None

# --- Discord Bot 發送邏輯 ---
async def send_via_bot(message_text):
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f"🤖 Bot 已登入：{client.user.name}")
        channel = client.get_channel(int(CHANNEL_ID))
        if channel:
            await channel.send(message_text)
            print("✅ 訊息已透過 Bot 成功發送！")
        else:
            print("❌ 找不到指定頻道，請確認 CHANNEL_ID 是否正確以及 Bot 是否已被邀請進伺服器。")
        await client.close()  # 發送完成後自動斷開連線，結束 GitHub Action Task

    await client.start(DISCORD_TOKEN)

if __name__ == "__main__":
    flight_msg = fetch_flight_data()
    if flight_msg and DISCORD_TOKEN and CHANNEL_ID:
        asyncio.run(send_via_bot(flight_msg))
    else:
        print("未抓取到資料或 Secrets 設定缺失。")
