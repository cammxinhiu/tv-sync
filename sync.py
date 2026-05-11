import requests
import json
import sys
import os

SOURCE_URL = "https://pub-26bab83910ab4b5781549d12d2f0ef6f.r2.dev/hoiquan1.json"
FILE_NAME = "hoiquan.json"

# 1. Tải dữ liệu mới nhất từ nguồn về
try:
    r = requests.get(SOURCE_URL, timeout=10)
    r.raise_for_status() # Bắt lỗi nếu web nguồn bị sập (404, 500...)
    new_data = r.json()
except Exception as e:
    print(f"Lỗi khi tải dữ liệu: {e}")
    sys.exit(1) # Lỗi thì thoát luôn, báo đỏ bên Actions để sếp dễ biết

# 2. Mở file cũ ra để đối chiếu (nếu file đã tồn tại)
old_data = None
if os.path.exists(FILE_NAME):
    with open(FILE_NAME, "r", encoding="utf-8") as f:
        try:
            old_data = json.load(f)
        except json.JSONDecodeError:
            pass # Nếu file cũ lỗi định dạng thì coi như trắng, ghi đè luôn

# 3. Tiến hành so sánh
if new_data == old_data:
    print("Dữ liệu không có thay đổi (chưa có trận mới). Dừng script!")
    sys.exit(0) # Ngắt ngang tại đây, không ghi file mới

# 4. Nếu là dữ liệu mới -> Lưu vào file hoiquan.json
with open(FILE_NAME, "w", encoding="utf-8") as f:
    json.dump(new_data, f, ensure_ascii=False, indent=2)

print("Đã cập nhật trận đấu mới thành công!")
