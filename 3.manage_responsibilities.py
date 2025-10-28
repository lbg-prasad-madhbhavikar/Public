import json
import pathlib


with open(pathlib.Path("./20.json"), 'r', encoding='utf-8') as f:
    responsibilities = json.load(f)
    for responsibility in responsibilities:
        id = responsibility.get("id")
        if pathlib.Path(f"dump/{id}").exists():
            with open(f"dump/{id}/responsibility.json", "w", encoding="utf-8") as f:
                json.dump(responsibility, f, indent=2)