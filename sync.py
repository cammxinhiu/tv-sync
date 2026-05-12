import requests
import json
import sys
import os
import time

# 1. Thêm cái đuôi ?t=thời_gian_thực để phá nát cache của Cloudflare
# Mỗi lần chạy link sẽ khác nhau 1 xíu, ép Cloudflare phải tải file mới
SOURCE_URL = f"https://pub-26bab83910ab4b5781549d12d2f0ef6f.r2.dev/hoiquan1.json?t={int(time.time())}"
FILE_NAME = "hoiquan.json"

try:
    # Giả lập làm người dùng thật bằng trình duyệt để không bị chặn
    headers = {
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
    }
    r = requests.get(SOURCE_URL, headers=headers, timeout=10)
    r.raise_for_status()
    new_data = r.json()
except Exception as e:
    print(f"Lỗi khi tải dữ liệu: {e}")
    sys.exit(1)

# 2. XỬ LÝ LỌC TRẬN ĐẤU (Không lo phân biệt hoa/thường)
if "groups" in new_data:
    for group in new_data["groups"]:
        if group.get("id") == "live" and "channels" in group:
            valid_channels = []
            for channel in group["channels"]:
                is_active = False
                if "labels" in channel:
                    for label in channel["labels"]:
                        # Ép tất cả về chữ thường (lowercase) để quét
                        text = label.get("text", "").lower()
                        # Lấy tất cả các nhãn có chứa chữ "live"
                        # Loại bỏ ngay lập tức nếu có chứa chữ "end" hoặc "kết thúc"
                        if "live" in text and "end" not in text and "kết thúc" not in text:
                            is_active = True
                            break
                
                if is_active:
                    valid_channels.append(channel)
            
            group["channels"] = valid_channels

# 3. So sánh với file cũ
old_data = None
if os.path.exists(FILE_NAME):
    with open(FILE_NAME, "r", encoding="utf-8") as f:
        try:
            old_data = json.load(f)
        except json.JSONDecodeError:
            pass

if new_data == old_data:
    print("Cloudflare đã nhả data mới, nhưng nội dung không có gì thay đổi. Dừng script!")
    sys.exit(0)

# 4. Lưu dữ liệu
with open(FILE_NAME, "w", encoding="utf-8") as f:
    json.dump(new_data, f, ensure_ascii=False, indent=2)

print("Phát hiện trận mới/trạng thái mới! Đã dọn dẹp sạch sẽ và cập nhật file thành công.")
