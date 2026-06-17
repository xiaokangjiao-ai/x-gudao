import json
from pathlib import Path

d = json.loads(Path("output/IWM.json").read_text(encoding="utf-8"))
print("Keys:", list(d.keys()))
print("ticker:", d.get("ticker"))
print("name:", d.get("name"))
print("category:", d.get("category"))
print("generated_at:", d.get("generated_at"))
print("data[0]:", d.get("data", [{"date": "N/A"}])[0])
print("data[-1]:", d.get("data", [{}])[-1])
print("Total rows:", len(d.get("data", [])))
