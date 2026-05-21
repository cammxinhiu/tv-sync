import re
import json
import uuid
import requests

M3U_URL = "https://raw.githubusercontent.com/cammxinhiu/tv-sync/main/bongda.m3u"

GROUP_CONFIG = {
    "lương sơn": {
        "id": "luongson",
        "name": "🏔️ Lương Sơn",
        "color": "#378ADD"
    },
    "khán đài a": {
        "id": "khandaia",
        "name": "🏟️ Khán Đài A",
        "color": "#D85A30"
    },
    "hội quán": {
        "id": "hoiquan_m3u",
        "name": "🏠 Hội Quán",
        "color": "#1cb57a"
    },
    "colalive": {
        "id": "colalive",
        "name": "🔴 Cola Live",
        "color": "#E24B4A"
    },
    "gà vàng": {
        "id": "gavang",
        "name": "🐔 Gà Vàng",
        "color": "#F5A623"
    },
    "socolive": {
        "id": "socolive",
        "name": "⚽ Socolive",
        "color": "#00B4D8"
    },
    "chuối chiên": {
        "id": "chuoichien",
        "name": "🍌 Chuối Chiên",
        "color": "#FFD166"
    },
}

r = requests.get(M3U_URL, timeout=15)
r.encoding = "utf-8"
lines = r.text.splitlines()

groups = {}
i = 0
while i < len(lines):
    line = lines[i].strip()
    if line.startswith("#EXTINF"):
        group_match = re.search(r'group-title="([^"]*)"', line)
        logo_match = re.search(r'tvg-logo="([^"]*)"', line)
        comma_idx = line.rfind(",")
        title = line[comma_idx+1:].strip() if comma_idx >= 0 else ""
        group_raw = group_match.group(1).strip().lower() if group_match else ""
        logo = logo_match.group(1) if logo_match else ""

        # Tìm URL stream
        url = ""
        j = i + 1
        while j < len(lines):
            next_line = lines[j].strip()
            if next_line.startswith("#EXTINF"):
                break
            if next_line and not next_line.startswith("#"):
                url = next_line
                break
            j += 1

        # Chỉ lấy HLS, đúng group
        if url and ".m3u8" in url and group_raw in GROUP_CONFIG:
            cfg = GROUP_CONFIG[group_raw]
            gid = cfg["id"]

            if gid not in groups:
                groups[gid] = {
                    "id": gid,
                    "name": cfg["name"],
                    "display": "vertical",
                    "grid_number": 2,
                    "enable_detail": False,
                    "channels": []
                }

            # Làm sạch tên trận
            clean_title = re.sub(r'\s*\([^)]+\)\s*', ' ', title).strip()
            clean_title = re.sub(r'\b(sd_\d+|hd_\d+|source|sd|hd|flv|m3u)\b', '', clean_title, flags=re.IGNORECASE).strip()
            clean_title = re.sub(r'\s+', ' ', clean_title).strip()

            # Lấy giờ
            time_match = re.search(r'(\d{1,2}h\d{2})', title)
            time_str = time_match.group(1) if time_match else ""

            # BLV
            blv_match = re.search(r'BLV\s+([^\s(]+)', title, re.IGNORECASE)
            blv = "BLV " + blv_match.group(1).strip() if blv_match else cfg["name"]

            channel_id = f"{gid}-{uuid.uuid4().hex[:10]}"
            link_id = f"lnk-{uuid.uuid4().hex[:8]}"

            channel = {
                "id": channel_id,
                "name": f"⚽ {clean_title}",
                "type": "single",
                "display": "thumbnail-only",
                "enable_detail": False,
                "image": {
                    "padding": 1,
                    "background_color": "#1a1a2e",
                    "display": "contain",
                    "url": logo,
                    "width": 400,
                    "height": 300
                },
                "labels": [{
                    "text": f"● {time_str}" if time_str else "● Live",
                    "position": "top-left",
                    "color": "#00ffffff",
                    "text_color": "#ff0000"
                }],
                "sources": [{
                    "id": channel_id,
                    "name": blv,
                    "contents": [{
                        "id": channel_id,
                        "name": clean_title,
                        "streams": [{
                            "id": channel_id,
                            "name": "F",
                            "stream_links": [{
                                "id": link_id,
                                "name": "Link 1",
                                "type": "hls",
                                "default": True,
                                "url": url
                            }]
                        }]
                    }]
                }]
            }
            groups[gid]["channels"].append(channel)
    i += 1

# Bỏ duplicate — cùng tên trận giữ link đầu tiên
for gid in groups:
    seen = set()
    unique = []
    for ch in groups[gid]["channels"]:
        key = ch["name"]
        if key not in seen:
            seen.add(key)
            unique.append(ch)
    groups[gid]["channels"] = unique

# Sắp xếp group theo thứ tự config
ordered_groups = []
for key, cfg in GROUP_CONFIG.items():
    gid = cfg["id"]
    if gid in groups:
        ordered_groups.append(groups[gid])

output = {
    "id": "multisource",
    "name": "TV Stream",
    "color": "#1cb57a",
    "grid_number": 3,
    "groups": ordered_groups
}

with open("multisource.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

total = sum(len(g["channels"]) for g in ordered_groups)
print(f"Done! {len(ordered_groups)} nguồn, {total} trận → multisource.json")
for g in ordered_groups:
    print(f"  {g['name']}: {len(g['channels'])} trận")
