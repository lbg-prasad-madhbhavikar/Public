import pathlib
import json

directory_path = "dump"

location = pathlib.Path(directory_path)
stats = {}
count = 0
highest_tables = 0
highest_columns = 0
for dir in location.iterdir():
    if dir.is_dir():
        json_file = dir / "runtime.stats.json"
        stats[dir.name] = {}
        columns_dir = dir / "COLUMNS"
        folder_count = 0
        column_json_count = 0
        total_column_count = 0
        if columns_dir.exists() and columns_dir.is_dir():
            for subfolder in columns_dir.iterdir():
                if subfolder.is_dir():
                    folder_count += 1
                    column_json_count += sum(
                        1 for f in subfolder.iterdir()
                        if f.is_file() and f.name.endswith(".column.json")
                    )
                if "columns" not in stats[dir.name]:
                    stats[dir.name]["columns"] = []
                stats[dir.name]["columns"].append(column_json_count)
                total_column_count += column_json_count
                if highest_columns < column_json_count:
                    highest_columns = column_json_count
                column_json_count = 0
                
                    
        stats[dir.name]["tables"] = folder_count
        if highest_tables < folder_count:
            highest_tables = folder_count
        stats[dir.name]["total_columns"] = total_column_count
        
        if json_file.exists():
            with open(json_file) as f:
                data = json.load(f)
                duration = data.get("duration", "unknown")
                # Ensure duration is always present, even if unknown or malformed
                try:
                    if duration.endswith("m"):
                        stats[dir.name]["duration"] = float(duration[:-1]) * 60
                    else:
                        stats[dir.name]["duration"] = float(duration[:-1])
                except Exception:
                    stats[dir.name]["duration"] = duration
                    print(f"Error processing duration for {dir.name}: {duration}")
                count += 1
        else:
            # If runtime.stats.json does not exist, set duration to "unknown"
            stats[dir.name]["duration"] = "unknown"

# Sort stats by duration, keeping all keys
# sorted_stats = dict(
#     sorted(
#         ((k, v) for k, v in stats.items() if k != "count"),
#         key=lambda item: (
#             item[1].get("duration", float("inf"))
#             if isinstance(item[1].get("duration", None), (int, float))
#             else float("inf")
#         )
#     )
# )
sorted_stats=stats
sorted_stats["count"] = count
sorted_stats["highest_table_count"] = highest_tables
sorted_stats["highest_column_count"] = highest_columns

with open(location / "master.stats.json", "w") as f:
    json.dump(sorted_stats, f, indent=2)