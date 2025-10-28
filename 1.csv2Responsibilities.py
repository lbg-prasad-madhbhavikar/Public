import csv
import json
import os
from datetime import datetime

responsibilities = []
config = { "targets":[]}

with open('collibra-456-2025-10-28.csv', newline='') as csvfile:
    reader = csv.reader(csvfile)
    i = 0
    for row in reader:
        i = i+1
        if i == 1:
            continue
        o = set()
        o.update(col for col in row[4:] if not col.startswith('http'))
        responsibilities.append({
            "id": row[0].split('/')[-1],
            "roles": {
                "Data Product Owner": [row[3]],
                "Ownership Delegated Authority": [
                    *o
                ]
        }})
        config["targets"].append({
            "Data Product Name 3 Link": row[0]
        })
    if os.path.exists("responsibilities.json"):
        ts = datetime.now().strftime("%d%m%y%H%M%S")
        backup_name = f"responsibilities.{ts}.json"
        os.rename("responsibilities.json", backup_name)
    with open("responsibilities.json", "w", encoding="utf-8") as f:
        json.dump(responsibilities, f, indent=2)
        
    if os.path.exists("scraping_targets_config.json"):
        ts = datetime.now().strftime("%d%m%y%H%M%S")
        backup_name = f"scraping_targets_config.{ts}.json"
        os.rename("scraping_targets_config.json", backup_name)
    with open("scraping_targets_config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)