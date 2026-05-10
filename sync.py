import requests
import json

SOURCE_URL = "https://pub-26bab83910ab4b5781549d12d2f0ef6f.r2.dev/hoiquan1.json"

r = requests.get(SOURCE_URL, timeout=10)
data = r.json()

with open("hoiquan.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("Done")
