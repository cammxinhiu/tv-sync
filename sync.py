import requests
import json
import sys
import os

SOURCE_URL = "https://pub-26bab83910ab4b5781549d12d2f0ef6f.r2.dev/hoiquan1.json"
FILE_NAME = "hoiquan.json"

# 1. Tải dữ liệu từ nguồn
try:
    r = requests.get(SOURCE_URL, timeout=10)
    r.raise_for_status()
    new_data = r.json()
except Exception as e:
    print(f"Lỗi khi tải dữ liệu: {e}")
    sys.exit(1)

# 2. XỬ LÝ LỌC TRẬN ĐẤU (Bỏ các trận đã End)
# Tìm đến mảng groups -> tìm cái group có id là "live" -> lọc mảng "channels"
if "groups" in new_data:
    for group in new_data["groups"]:
        if group.get("id") == "live" and "channels" in group:
            valid_channels = []
            for channel in group["channels"]:
                is_active = False
                # Kiểm tra trong các labels của channel này
                if "labels" in channel:
                    for label in channel["labels"]:
                        text = label.get("text", "")
                        # Chỉ giữ lại nếu là "● Live" hoặc "⏳ Chưa live"
                        if "Live" in text or "Chưa live" in text:
                            is_active = True
                            break
                
                if is_active:
                    valid_channels.append(channel)
            
            # Ghi đè danh sách channels đã lọc (chỉ còn live/chưa live)
            group["channels"] = valid_channels

# 3. Mở file cũ ra để đối chiếu
old_data = None
if os.path.exists(FILE_NAME):
    with open(FILE_NAME, "r", encoding="utf-8") as f:
        try:
            old_data = json.load(f)
        except json.JSONDecodeError:
            pass

# 4. Tiến hành so sánh
if new_data == old_data:
    print("Dữ liệu không có thay đổi (chưa có trận mới hoặc trạng thái mới). Dừng script!")
    sys.exit(0)

# 5. Lưu vào file
with open(FILE_NAME, "w", encoding="utf-8") as f:
    json.dump(new_data, f, ensure_ascii=False, indent=2)

print("Đã cập nhật dữ liệu trận đấu thành công (đã dọn dẹp trận cũ)!")
