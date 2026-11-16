import json

with open("data.json", "r", encoding="utf-8") as f:     # data 파일로드
    data = json.load(f)

print(data)