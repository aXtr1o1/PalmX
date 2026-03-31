import csv
import os
import json
import datetime
import uuid
import pandas as pd
from openai import AzureOpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Config ---
OLD_LEADS_PATH = "/Volumes/ReserveDisk/codeBase/PalmX/runtime/leads/leads.csv"
OLD_SEED_PATH = "/Volumes/ReserveDisk/codeBase/PalmX/runtime/leads/leads_seed.csv"
NEW_DATA_DIR = "/Volumes/ReserveDisk/codeBase/PalmX/runtime/leads/New_liveData"
OUTPUT_LEADS_PATH = "/Volumes/ReserveDisk/codeBase/PalmX/runtime/leads/leads.csv"
OUTPUT_SEED_PATH = "/Volumes/ReserveDisk/codeBase/PalmX/runtime/leads/leads_seed.csv"

# Azure OpenAI Setup
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
AZURE_OPENAI_CHAT_DEPLOYMENT = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o")

client = AzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    api_version=AZURE_OPENAI_API_VERSION,
    azure_endpoint=AZURE_OPENAI_ENDPOINT
)

TARGET_COLUMNS = [
    "timestamp", "session_id", "name", "phone", 
    "interest_projects", "preferred_region", "unit_type", 
    "budget_min", "budget_max", "purpose", "timeline", 
    "next_step", "lead_summary", "tags", "temperature", "kb_version_hash"
]

def normalize_old_seed(df):
    """Map legacy leads_seed.csv fields to target schema."""
    if df.empty: return df
    
    mapping = {
        "created_at": "timestamp",
        "uuid": "session_id",
        "interest_projects": "interest_projects",
        "name": "name",
        "phone": "phone",
        "preferred_region": "preferred_region",
        "unit_type": "unit_type",
        "budget_min": "budget_min",
        "budget_max": "budget_max",
        "purpose": "purpose",
        "timeline": "timeline",
        "next_step": "next_step",
        "lead_summary": "lead_summary",
        "tags": "tags",
        "kb_version_hash": "kb_version_hash"
    }
    
    # Rename matching columns
    df = df.rename(columns={k: v for k, v in mapping.items() if k in df.columns})
    
    # Ensure all target columns exist
    for col in TARGET_COLUMNS:
        if col not in df.columns:
            df[col] = ""
            
    return df[TARGET_COLUMNS]

def classify_batch(leads_batch):
    """Classify a batch of leads using LLM."""
    if not leads_batch:
        return []
        
    prompt = f"""
    Classify the temperature (Hot, Warm, Cold) for the following real estate leads based on their summary and attributes.
    Criteria:
    - Hot: Immediate intent, clear budget, high engagement.
    - Warm: Interested but 3-6 month timeline, or moderate budget/engagement.
    - Cold: Random inquiry, vague intent, or very long timeline.
    
    Leads:
    {json.dumps(leads_batch, indent=2)}
    
    Return a JSON array of classifications:
    [
        {{"index": 0, "temperature": "Hot/Warm/Cold"}},
        ...
    ]
    """
    
    try:
        resp = client.chat.completions.create(
            model=AZURE_OPENAI_CHAT_DEPLOYMENT,
            messages=[
                {"role": "system", "content": "You are a sales intelligence assistant."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0
        )
        data = json.loads(resp.choices[0].message.content)
        return data.get("classifications", data.get("results", [])) # Handle variations in response key
    except Exception as e:
        print(f"Error in batch classification: {e}")
        return []

def main():
    print("--- Starting Lead Data Augmentation ---")
    
    # 1. Load Old Leads
    print("Loading existing leads...")
    df_leads_old = pd.read_csv(OLD_LEADS_PATH, dtype=str)
    df_seed_old = pd.read_csv(OLD_SEED_PATH, dtype=str)
    
    # 2. Normalize Schema
    print("Normalizing schemas...")
    df_seed_old = normalize_old_seed(df_seed_old)
    
    # Ensure df_leads_old has temperature column
    if "temperature" not in df_leads_old.columns:
        df_leads_old["temperature"] = ""
    
    # Combine old leads and drop duplicates (by session_id/uuid if possible, or just concat)
    combined_old = pd.concat([df_leads_old, df_seed_old], ignore_index=True)
    combined_old = combined_old.drop_duplicates(subset=["session_id", "name"], keep='first')
    
    print(f"Found {len(combined_old)} unique old leads.")

    # 3. Handle Temperature Backfill
    needs_temp = combined_old[combined_old["temperature"].isna() | (combined_old["temperature"] == "")]
    print(f"{len(needs_temp)} leads need temperature backfill.")
    
    if not needs_temp.empty:
        batch_size = 20
        all_classifications = {}
        
        leads_list = needs_temp.to_dict('records')
        for i in range(0, len(leads_list), batch_size):
            batch = leads_list[i : i + batch_size]
            print(f"Classifying batch {i // batch_size + 1}...")
            
            # Prepare minimal data for LLM to save tokens
            minimal_batch = []
            for idx, lead in enumerate(batch):
                minimal_batch.append({
                    "index": i + idx,
                    "summary": lead.get("lead_summary", ""),
                    "tags": lead.get("tags", ""),
                    "timeline": lead.get("timeline", ""),
                    "budget": f"{lead.get('budget_min')} - {lead.get('budget_max')}"
                })
            
            results = classify_batch(minimal_batch)
            for res in results:
                idx = res.get("index")
                temp = res.get("temperature")
                if idx is not None and temp:
                    # Map back to the original index in leads_list
                    # The LLM returned 'index' relative to the batch start offset i
                    # Wait, LLM returned index 0-19 for a batch. I need to map it to absolute index.
                    # My prompt said 'index: 0, 1...', so it will likely return indices 0-19.
                    # Or it might return the absolute index I gave it.
                    # Let's assume it returns the absolute index I gave it.
                    all_classifications[idx] = temp
        
        # Apply classifications
        for idx, temp in all_classifications.items():
            combined_old.at[needs_temp.index[idx], "temperature"] = temp
            
    # 4. Load New Live Leads
    print("Loading new live data...")
    new_leads_path = os.path.join(NEW_DATA_DIR, "leads.csv")
    new_seed_path = os.path.join(NEW_DATA_DIR, "leads_seed.csv")
    
    df_new_leads = pd.read_csv(new_leads_path, dtype=str)
    df_new_seed = pd.read_csv(new_seed_path, dtype=str)
    
    # Combine and deduplicate new data
    combined_new = pd.concat([df_new_leads, df_new_seed], ignore_index=True)
    combined_new = combined_new.drop_duplicates(subset=["session_id", "name"], keep='first')
    
    print(f"Found {len(combined_new)} unique new leads from generation.")

    # 5. Final Merge
    print("Merging old and new datasets...")
    final_df = pd.concat([combined_old, combined_new], ignore_index=True)
    
    # Final deduplication by session_id/name across both sets
    final_df = final_df.drop_duplicates(subset=["session_id", "name"], keep='last')
    
    # Sort by timestamp (handle potential mixed formats if any)
    final_df["timestamp_dt"] = pd.to_datetime(final_df["timestamp"], errors='coerce')
    final_df = final_df.sort_values(by="timestamp_dt", ascending=False).drop(columns=["timestamp_dt"])
    
    print(f"Total leads after merge: {len(final_df)}")

    # 6. Save back
    print("Saving to original locations...")
    # Backup first
    if os.path.exists(OUTPUT_LEADS_PATH):
        os.rename(OUTPUT_LEADS_PATH, OUTPUT_LEADS_PATH + ".bak")
    if os.path.exists(OUTPUT_SEED_PATH):
        os.rename(OUTPUT_SEED_PATH, OUTPUT_SEED_PATH + ".bak")
        
    final_df.to_csv(OUTPUT_LEADS_PATH, index=False)
    final_df.to_csv(OUTPUT_SEED_PATH, index=False)
    
    print("Consolidation complete!")

if __name__ == "__main__":
    main()
