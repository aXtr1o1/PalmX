import sys
import os
import csv

# Add repo root to path
sys.path.append(os.getcwd())

try:
    from app.backend.config import Config
except ImportError:
    # Fallback if run from backend dir
    sys.path.append(os.path.dirname(os.getcwd()))
    try:
        from app.backend.config import Config
    except ImportError:
         # Hardcoded fallback for debugging
         class Config:
             LEADS_PATH = "runtime/leads/leads.csv"

print(f"--- Debugging Leads (CSV Mode) ---")
print(f"Config.LEADS_PATH: {Config.LEADS_PATH}")

if os.path.exists(Config.LEADS_PATH):
    print(f"[OK] File exists.")
    file_size = os.path.getsize(Config.LEADS_PATH)
    print(f"File Size: {file_size} bytes")
    
    print("\n--- CSV Reader Test ---")
    try:
        with open(Config.LEADS_PATH, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
            print(f"Total Rows: {len(rows)}")
            if rows:
                print(f"Headers: {rows[0]}")
            if len(rows) > 1:
                print("Last Row:")
                print(rows[-1])
            else:
                print("Only headers found (No data).")
    except Exception as e:
        print(f"[ERROR] CSV read failed: {e}")

else:
    print(f"[ERROR] File NOT found at {Config.LEADS_PATH}")
