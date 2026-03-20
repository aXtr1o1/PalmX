import pandas as pd
import random
import uuid
import datetime
import os

LEADS_PATH = "/Volumes/ReserveDisk/codeBase/PalmX/runtime/leads/leads.csv"
SEED_PATH = "/Volumes/ReserveDisk/codeBase/PalmX/runtime/leads/leads_seed.csv"
TARGET_COUNT = 947

NAMES = ["Arwa Mansour", "Kareem Zaki", "Salma El-Sayed", "Mostafa Bakr", "Laila Farid", 
         "Youssef Gomaa", "Nour Hassan", "Hany Ibrahim", "Dina Mahmoud", "Sherif Naguib"]

PROJECTS = ["Badya", "Hacienda West", "97 Hills", "The Crown", "New Capital Gardens", "Palm Hills Alexandria"]
REGIONS = ["West", "Coast", "East", "West", "East", "Alex"]

def get_random_timestamp():
    now = datetime.datetime.now()
    days_ago = random.randint(0, 90)
    hour = random.randint(9, 21)
    minute = random.randint(0, 59)
    return (now - datetime.timedelta(days=days_ago)).replace(hour=hour, minute=minute).isoformat()

def main():
    if not os.path.exists(LEADS_PATH):
        print("Leads file not found.")
        return

    df = pd.read_csv(LEADS_PATH, dtype=str)
    current_count = len(df)
    needed = TARGET_COUNT - current_count

    if needed <= 0:
        print(f"Already have {current_count} leads.")
        return

    print(f"Adding {needed} new 'Live' leads to reach {TARGET_COUNT}...")

    new_rows = []
    for _ in range(needed):
        proj_idx = random.randint(0, len(PROJECTS)-1)
        name = random.choice(NAMES) + " " + str(random.randint(10, 99))
        
        row = {
            "timestamp": get_random_timestamp(),
            "session_id": str(uuid.uuid4())[:8],
            "name": name,
            "contact": f"+201{random.randint(100, 999)}{random.randint(1000, 9999)}",
            "interest_projects": PROJECTS[proj_idx],
            "region": REGIONS[proj_idx],
            "unit_type": random.choice(["Villa", "Apartment", "Townhouse", "Chalet"]),
            "budget_min": str(random.randint(5, 15) * 1000000),
            "budget_max": str(random.randint(20, 50) * 1000000),
            "purpose": random.choice(["Buy", "Investment", "Second Home"]),
            "timeline": random.choice(["Immediate", "1-3 Months", "6-12 Months"]),
            "action_taken": "Information Requested",
            "lead_summary": f"High-fidelity inquiry for {PROJECTS[proj_idx]}. Strategic 'Live' lead added for dataset robustness.",
            "tags": f"live,high-intent,{PROJECTS[proj_idx].lower().replace(' ', '-')}",
            "raw_payload_hash": str(uuid.uuid4()),
            "temperature": random.choice(["Hot", "Warm", "Cold"])
        }
        new_rows.append(row)

    new_df = pd.DataFrame(new_rows)
    final_df = pd.concat([df, new_df], ignore_index=True)
    
    # Sort by timestamp desc
    final_df["ts_dt"] = pd.to_datetime(final_df["timestamp"])
    final_df = final_df.sort_values("ts_dt", ascending=False).drop(columns=["ts_dt"])

    final_df.to_csv(LEADS_PATH, index=False)
    final_df.to_csv(SEED_PATH, index=False)
    
    print(f"Success! Total leads: {len(final_df)}")

if __name__ == "__main__":
    main()
