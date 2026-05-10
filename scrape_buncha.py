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
        # Lấy match_id từ cuối URL: /truc-tiep/slug/601450240
        parts = href.rstrip("/").split("/")
        if len(parts) < 2:
            continue
        match_id = parts[-1]
        if not match_id.isdigit():
            continue
        
        # Tên trận từ text trong card
        name = a.get_text(" ", strip=True)
        # Thumbnail logo đội nhà
        img = a.select_one("img[src*='team']")
        thumb = img["src"] if img else ""
        
        matches.append({
            "match_id": match_id,
            "name": name[:80],  # cắt bớt nếu quá dài
            "thumb": thumb,
            "href": href,
        })
    
    # Bỏ duplicate theo match_id
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
        browser = await p.chromium.launch(args=["--no-sandbox"])
        page = await browser.new_page()
        
        # Intercept mọi request, lọc lấy .m3u8
        async def handle_request(request):
            nonlocal m3u8_url
            if ".m3u8" in request.url and m3u8_url is None:
                m3u8_url = request.url
        
        page.on("request", handle_request)
        
        try:
            await page.goto(player_url, timeout=15000)
            await page.wait_for_timeout(8000)  # chờ JS load và gọi stream
        except Exception as e:
            print(f"  Timeout/error: {e}")
        finally:
            await browser.close()
    
    return m3u8_url

def get_channel_id(match_id):
    """Lấy channel_id từ trang trận cụ thể"""
    url = f"https://bunchatv4.net/truc-tiep"
    # channel_id nằm trong href của iframe: cbox-v2...?match_id=...&channel_id=...
    try:
        r = requests.get(f"https://bunchatv4.net/", headers=HEADERS, timeout=10)
        match = re.search(
            rf"match_id={match_id}&(?:amp;)?channel_id=(\d+)", r.text
        )
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
    print("Scraping match list...")
    matches = scrape_matches()
    print(f"Found {len(matches)} matches")
    
    # Chỉ lấy stream cho 5 trận đầu (tránh timeout GitHub Actions)
    for i, match in enumerate(matches[:5]):
        print(f"[{i+1}] Getting stream for match_id={match['match_id']}...")
        
        # Thử lấy channel_id từ trang homepage
        channel_id = get_channel_id(match["match_id"]) or "0"
        m3u8 = await get_stream_url(match["match_id"], channel_id)
        match["m3u8"] = m3u8
        print(f"    → {'Found: ' + m3u8[:60] if m3u8 else 'No stream found'}")
    
    # Các trận còn lại không có stream link (chưa live)
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
    
    print(f"Done! Saved {len(matches)} channels to buncha.json")

if __name__ == "__main__":
    asyncio.run(main())
