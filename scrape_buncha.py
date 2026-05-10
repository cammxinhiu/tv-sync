import asyncio
import json
import uuid
import re
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def scrape_matches():
    """Lấy danh sách trận từ homepage"""
    r = requests.get("https://bunchatv4.net/truc-tiep", headers=HEADERS, timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")
    
    matches = []
    for a in soup.select("a[href*='/truc-tiep/']"):
        href = a.get("href", "")
        parts = href.rstrip("/").split("/")
        if len(parts) < 2:
            continue
        match_id = parts[-1]
        if not match_id.isdigit():
            continue
        
        name = a.get_text(" ", strip=True)
        
        # Thử nhiều cách tìm ảnh
        img = a.select_one("img") or a.find_parent().select_one("img") if a.find_parent() else None
        thumb = ""
        if img and img.get("src"):
            thumb = img["src"]
            if not thumb.startswith("http"):
                thumb = "https://bunchatv4.net" + thumb
        
        # Fallback: dùng logo mặc định
        if not thumb:
            thumb = "https://bunchatv4.net/themes/default/images/logo.svg"
        
        matches.append({
            "match_id": match_id,
            "name": name[:80],
            "thumb": thumb,
            "href": href,
        })
    
    # Bỏ duplicate
    seen = set()
    unique = []
    for m in matches:
        if m["match_id"] not in seen:
            seen.add(m["match_id"])
            unique.append(m)
    
    return unique

async def get_stream_url(match_id, channel_id):
    """Dùng Playwright để intercept URL M3U8 từ iframe player"""
    player_url = f"https://cbox-v2.bunchatv2.com/?match_id={match_id}&channel_id={channel_id}"
    m3u8_url = None
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=["--no-sandbox", "--disable-blink-features=AutomationControlled"])
        page = await browser.new_page()
        
        # Bắt RESPONSE thay vì request
        async def handle_response(response):
            nonlocal m3u8_url
            if ".m3u8" in response.url and m3u8_url is None:
                m3u8_url = response.url
                print(f"    ✓ Caught M3U8: {m3u8_url[:80]}")
        
        page.on("response", handle_response)
        
        try:
            await page.goto(player_url, wait_until="networkidle", timeout=20000)
            await page.wait_for_timeout(12000)  # Chờ 12s
        except Exception as e:
            print(f"  ⚠ Error: {e}")
        finally:
            await browser.close()
    
    return m3u8_url

def get_channel_id(match_id):
    """Lấy channel_id từ trang homepage"""
    try:
        r = requests.get("https://bunchatv4.net/", headers=HEADERS, timeout=10)
        match = re.search(rf"match_id={match_id}&(?:amp;)?channel_id=(\d+)", r.text)
        if match:
            return match.group(1)
    except:
        pass
    return None

def build_channel(match):
    """Build channel object theo schema hoiquan.json"""
    channel_id = f"buncha-{uuid.uuid4().hex[:12]}"
    streams = []
    
    if match.get("m3u8"):
        streams = [{
            "id": channel_id,
            "name": "F",
            "stream_links": [{
                "id": f"lnk-{uuid.uuid4().hex[:10]}",
                "name": "Link 1",
                "type": "hls",
                "default": True,
                "url": match["m3u8"]
            }]
        }]
    
    return {
        "id": channel_id,
        "name": f"⚽ {match['name']}",
        "type": "single",
        "display": "thumbnail-only",
        "enable_detail": False,
        "image": {
            "padding": 1,
            "background_color": "#1a1a2e",
            "display": "contain",
            "url": match.get("thumb", ""),
            "width": 1600,
            "height": 1200
        },
        "labels": [{
            "text": "● Live" if match.get("m3u8") else "⏳ Chưa live",
            "position": "top-left",
            "color": "#00ffffff",
            "text_color": "#ff0000" if match.get("m3u8") else "#d54f1a"
        }],
        "sources": [{
            "id": channel_id,
            "name": "Bún Chả TV",
            "contents": [{
                "id": channel_id,
                "name": match["name"],
                "streams": streams
            }]
        }]
    }

async def main():
    print("🔍 Scraping match list...")
    matches = scrape_matches()
    print(f"✅ Found {len(matches)} matches\n")
    
    # DEBUG: In ra 3 trận đầu
    for m in matches[:3]:
        print(f"  📌 {m['name'][:45]}")
        print(f"     Thumb: {m['thumb'][:60]}\n")
    
    # Lấy stream cho 5 trận đầu
    for i, match in enumerate(matches[:5]):
        print(f"[{i+1}/5] 🎯 Getting stream for: {match['name'][:45]}")
        print(f"        Player: https://cbox-v2.bunchatv2.com/?match_id={match['match_id']}&channel_id=...")
        
        channel_id = get_channel_id(match["match_id"]) or "0"
        m3u8 = await get_stream_url(match["match_id"], channel_id)
        match["m3u8"] = m3u8
        
        if m3u8:
            print(f"        ✅ Stream found: {m3u8[:80]}\n")
        else:
            print(f"        ❌ No stream (chưa live hoặc bị block)\n")
    
    # Các trận còn lại không có stream
    for match in matches[5:]:
        match["m3u8"] = None
    
    # Build JSON
    output = {
        "id": "bunchatv",
        "name": "Bún Chả TV",
        "color": "#e63946",
        "grid_number": 3,
        "image": {
            "type": "cover",
            "url": "https://bunchatv4.net/themes/default/images/logo.svg"
        },
        "groups": [{
            "id": "live",
            "name": "🔴 Live thể thao",
            "display": "vertical",
            "grid_number": 2,
            "enable_detail": False,
            "channels": [build_channel(m) for m in matches]
        }]
    }
    
    with open("buncha.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Done! Saved {len(matches)} channels to buncha.json")

if __name__ == "__main__":
    asyncio.run(main())
