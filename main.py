import os
import asyncio
import requests
from datetime import datetime, timedelta
import discord

# 1. 隱私 Secrets（只讀取 Token 與 SerpApi）
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
SERPAPI_KEY = os.getenv("SERPAPI_KEY")

# 2. 直接寫死目標頻道 ID (請替換為你的純數字 ID)
TARGET_CHANNEL_ID = 1560638536800014407 

def fetch_flight_data():
    # 使用具體的機場與城市代碼
    origin = "TPE"         # 台北桃園 (TPE)
    destination = "TYO"    # 東京全機場 (TYO)

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
        "type": "1",           # 1 代表來回票 (Round trip)，2 代表單程
        "currency": "TWD",
        "hl": "zh-TW",
        "api_key": SERPAPI_KEY
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        # 如果 SerpApi 報錯
        if "error" in data:
            print(f"❌ SerpApi 報錯: {data['error']}")
            
            # 💡 備用方案：如果 TYO 查不到，改用 NRT (成田機場) 試試
            print("🔄 嘗試切換目的地為 NRT (成田機場) 重新查詢...")
            params["arrival_id"] = "NRT"
            response = requests.get(url, params=params)
            data = response.json()
            if "error" in data:
                print(f"❌ 備用查詢依然報錯: {data['error']}")
                return None

        # 彙整航班資料
        all_flights = []
        if "best_flights" in data:
            all_flights.extend(data["best_flights"])
        if "other_flights" in data:
            all_flights.extend(data["other_flights"])

        if not all_flights:
            print("⚠️ 未找到任何航班列表。")
            return None

        airline_best_prices = {}
        for flight in all_flights:
            price = flight.get("price")
            flights_list = flight.get("flights", [])
            
            if flights_list:
                airline_name = flights_list[0].get("airline", "未知航空")
            else:
                airline_name = "未知航空"
            
            if price:
                if airline_name not in airline_best_prices or price < airline_best_prices[airline_name]:
                    airline_best_prices[airline_name] = price

        if not airline_best_prices:
            print("⚠️ 未能提取出價格。")
            return None

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
        print(f"❌ 解析機票數據時發生例外錯誤: {e}")
        return None
        airline_best_prices = {}
        for flight in all_flights:
            price = flight.get("price")
            flights_list = flight.get("flights", [])
            
            if flights_list:
                airline_name = flights_list[0].get("airline", "未知航空")
            else:
                airline_name = "未知航空"
            
            if price:
                if airline_name not in airline_best_prices or price < airline_best_prices[airline_name]:
                    airline_best_prices[airline_name] = price

        if not airline_best_prices:
            print("⚠️ 有找到航班資料，但無法提取出價格與航空公司。")
            return None

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
        print(f"❌ 解析機票數據時發生例外錯誤: {e}")
        return None

# --- Discord Bot 發送邏輯 ---
async def send_via_bot(message_text):
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f"🤖 Bot 已成功登入：{client.user.name} (ID: {client.user.id})")
        
        try:
            # 使用 fetch_channel 強制向 Discord API 抓取頻道物件（避免 get_channel 快取拿到 None）
            channel = await client.fetch_channel(TARGET_CHANNEL_ID)
            await channel.send(message_text)
            print("✅ 訊息已成功推送到指定頻道！")
        except discord.errors.Forbidden:
            print("❌ 發送失敗：Bot 沒有權限存取該頻道（請檢查頻道權限是否允許 Bot 檢視與發言）。")
        except discord.errors.NotFound:
            print("❌ 發送失敗：找不到該頻道 ID，請確認頻道 ID 是否複製正確。")
        except Exception as e:
            print(f"❌ 發送訊息時發生未知錯誤: {e}")
            
        await client.close()

    await client.start(DISCORD_TOKEN)

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("❌ 錯誤：找不到 DISCORD_TOKEN，請檢查 GitHub Secrets！")
    else:
        print("🔍 開始抓取機票數據...")
        flight_msg = fetch_flight_data()
        
        if flight_msg:
            print("🚀 數據抓取成功，準備啟動 Bot 發送訊息...")
            asyncio.run(send_via_bot(flight_msg))
        else:
            print("⚠️ 未能產生機票訊息（可能是 API 未回傳數據），取消發送。")
