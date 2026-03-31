import os
import pandas as pd
import requests
import json
import time
from dotenv import load_dotenv

load_dotenv()

# Azure OpenAI Config
API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
DEPLOYMENT = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o")
API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")

URL = f"{ENDPOINT}/openai/deployments/{DEPLOYMENT}/chat/completions?api-version={API_VERSION}"

LEADS_PATH = "/Volumes/ReserveDisk/codeBase/PalmX/runtime/leads/leads.csv"
SEED_PATH = "/Volumes/ReserveDisk/codeBase/PalmX/runtime/leads/leads_seed.csv"

def get_pro_summary_batch(leads_data):
    """
    leads_data: list of dicts with lead info
    """
    prompt = """
You are a high-end Real Estate Concierge for Palm Hills Developments. 
Your task is to write 'Realistic, Organic, and Professional' CRM summaries for the following leads.
These summaries should sound like natural notes taken by a human sales advisor.

Guidelines:
1. Mention project specifics naturally (e.g., Badya's 5-10-15 city concept, Hacienda's Mediterranean luxury, 97 Hills exclusivity on Middle Ring Road).
2. Use professional but organic language. Avoid robotic 'Client is interested in...' formulas.
3. Contextualize the Budget and Timeline.
4. Keep each summary between 2-4 sentences.
5. Return ONLY a JSON array of objects, each with 'summary' and 'tags' (list of strings).
Example: [{"summary": "...", "tags": ["Badya-Visionary", "West-Cairo-Elite"]}, ...]

Leads:
"""
    for i, lead in enumerate(leads_data):
        prompt += f"{i+1}. Name: {lead['name']}, Project: {lead['interest_projects']}, Region: {lead['preferred_region']}, Unit: {lead['unit_type']}, Budget: {lead['budget_max']} EGP, Purpose: {lead['purpose']}, Timeline: {lead['timeline']}, Temperature: {lead['temperature']}\n"

    headers = {
        "Content-Type": "application/json",
        "api-key": API_KEY
    }
    
    payload = {
        "messages": [
            {"role": "system", "content": "You are a luxury real estate sales advisor. Generate sophisticated summaries and professional segmentation tags."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 4000
    }

    try:
        response = requests.post(URL, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        content = result['choices'][0]['message']['content'].strip()
        # Strip markdown if present
        if content.startswith("```json"):
            content = content[7:-3].strip()
        return json.loads(content)
    except Exception as e:
        print(f"Error in batch: {e}")
        return [{"summary": None, "tags": []}] * len(leads_data)

def enrich():
    df = pd.read_csv(LEADS_PATH)
    print(f"Enriching {len(df)} leads with pro summaries and tags...")
    
    all_results = []
    batch_size = 20
    
    for i in range(0, len(df), batch_size):
        batch = df.iloc[i:i+batch_size].to_dict('records')
        print(f"Processing batch {i//batch_size + 1}/{(len(df)//batch_size)+1}...")
        results = get_pro_summary_batch(batch)
        
        # Fallback if GPT fails or returns wrong length
        if len(results) != len(batch):
            print(f"Warning: Batch size mismatch at {i}. Expected {len(batch)}, got {len(results)}")
            results = [{"summary": item.get('lead_summary', 'Inquiry regarding Palm Hills.'), "tags": []} for item in batch]
        
        all_results.extend(results)
        
        # Incremental save
        temp_df = df.iloc[0:len(all_results)].copy()
        temp_df['lead_summary'] = [r.get('summary') for r in all_results]
        temp_df['tags'] = [json.dumps(r.get('tags', [])) for r in all_results]
        temp_df.to_csv(LEADS_PATH + ".tmp", index=False)
        
        # Avoid aggressive rate limits
        time.sleep(0.5)

    df['lead_summary'] = [r.get('summary') for r in all_results]
    df['tags'] = [json.dumps(r.get('tags', [])) for r in all_results]
    
    # Final cleanup: ensure no Nones
    df['lead_summary'] = df['lead_summary'].fillna('Exploring Palm Hills luxury developments.')
    
    df.to_csv(LEADS_PATH, index=False)
    df.to_csv(SEED_PATH, index=False)
    if os.path.exists(LEADS_PATH + ".tmp"):
        os.remove(LEADS_PATH + ".tmp")
    print("Enrichment complete.")

if __name__ == "__main__":
    enrich()
