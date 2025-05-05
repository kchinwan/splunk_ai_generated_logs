import pandas as pd
import json
from log_preprocessing import flatten_log_entry

df = pd.read_csv("data/raw_logs/logs.csv")
logs = []

for _, row in df.iterrows():
    try:
        raw_data = json.loads(row["_raw"])
        raw_data["index"] = row["index"]
        logs.append(flatten_log_entry(raw_data))
    except Exception as e:
        print(f"Error parsing row: {e}")

# logs is now a list of flattened dictionaries
print('-----------example------------')
df_logs = pd.DataFrame(logs)
print(df_logs.columns)
df_logs.to_csv('flatlogs.csv')