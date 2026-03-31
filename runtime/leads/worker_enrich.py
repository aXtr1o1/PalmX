import os
import pandas as pd
import requests
import json
import time
import sys
from dotenv import load_dotenv

load_dotenv()

# Azure OpenAI Config
API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
DEPLOYMENT = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o")
API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")

URL = f"{ENDPOINT}/openai/deployments/{DEPLOYMENT}/chat/completions?api-version={API_VERSION}"

def get_pro_summary_batch(leads_data):
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

    headers = {"Content-Type": "application/json", "api-key": API_KEY}
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
        if content.startswith("```json"): content = content[7:-3].strip()
        return json.loads(content)
    except Exception as e:
        print(f"Error: {e}")
        return [{"summary": None, "tags": []}] * len(leads_data)

def enrich_chunk(input_path, output_path):
    df = pd.read_csv(input_path)
    print(f"Enriching chunk {input_path} ({len(df)} leads)...")
    all_results = []
    batch_size = 20
    for i in range(0, len(df), batch_size):
        batch = df.iloc[i:i+batch_size].to_dict('records')
        print(f"[{input_path}] Batch {i//batch_size + 1}/{(len(df)//batch_size)+1}...")
        results = get_pro_summary_batch(batch)
        if len(results) != len(batch):
            results = [{"summary": "Inquiry regarding Palm Hills.", "tags": []} for _ in batch]
        all_results.extend(results)
        time.sleep(0.5)
    
    df['lead_summary'] = [r.get('summary') for r in all_results]
    df['tags'] = [json.dumps(r.get('tags', [])) for r in all_results]
    df.to_csv(output_path, index=False)
    print(f"Chunk {input_path} complete.")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python worker.py input.csv output.csv")
    else:
        enrich_chunk(sys.argv[1], sys.argv[2])
