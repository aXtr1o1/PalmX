import csv
import random
import uuid
import hashlib
import datetime
import os
import json

# Configuration
KB_PATH = "engine-KB/PalmX-buyerKB.csv"
LEADS_OUTPUT_PATH = "runtime/leads/leads_seed.csv"
TARGET_LEAD_COUNT = 370  # Target similar to 350-400 range

# Constants for Generation
NAMES_FIRST = ["Ahmed", "Mohamed", "Fatima", "Sara", "Ali", "Omar", "Layla", "Nour", "Youssef", "Khalid", "Amira", "Hassan", "Zainab", "Mariam", "Ibrahim", "Hana", "Mahmoud", "Rania", "Tarek", "Dina", "Sherif", "Mona", "Karim", "Nada", "Hazem", "Yasmin", "Samir", "Salma", "Moustafa", "Heba"]
NAMES_LAST = ["Ali", "Ibrahim", "Hassan", "Mohamed", "Ahmed", "Mahmoud", "Said", "Osman", "Hussain", "Kamel", "Fawzy", "Soliman", "Mustafa", "Amer", "Salem", "Helmy", "Nassar", "Gaber", "Hamdy", "Farouk", "Zaki", "Metwally", "Radwan", "Mansour", "Ezzat"]

PURPOSES = ["Investment", "Personal Use", "Second Home", "Resale"]
TIMELINES = ["Immediate", "1-3 Months", "3-6 Months", "6-12 Months", "Flexible"]
NEXT_STEPS = ["Call Back", "Schedule Visit", "Send Brochure", "WhatsApp Follow-up", "Not Interested", "Meeting Scheduled"]
SOURCES = ["Facebook", "Instagram", "Website", "Referral", "Google Ads", "Walk-in", "Cold Call"]
UNIT_TYPES = ["Apartment", "Villa", "Townhouse", "Twin House", "Chalets", "Duplex", "Penthouse", "Studio"]


def compute_kb_hash(filepath):
    """Computes SHA-256 hash of the input file."""
    if not os.path.exists(filepath):
        return "unknown_hash"
    
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()

def generate_phone():
    """Generates a random Egyptian-like mobile number."""
    prefix = random.choice(["010", "011", "012", "015"])
    number = "".join([str(random.randint(0, 9)) for _ in range(8)])
    return f"{prefix}{number}"

def format_tags(tags_list):
    """Formats list of tags into string representation consistent with leads.csv."""
    # Based on leads.csv content (not shown fully but likely standard JSON or string array)
    # Assuming standard JSON-like format for safety: ["Tag1", "Tag2"]
    # Adjusting to replace single quotes with double quotes if needed, but json.dumps does standards.
    return json.dumps(tags_list)

def load_projects(kb_path):
    projects = []
    regions = set()
    with open(kb_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
             # Basic validation
            if row['project_name']:
                projects.append(row)
                if row['region']:
                    regions.add(row['region'])
    return projects, list(regions)

def generate_leads():
    print(f"Loading Knowledge Base from {KB_PATH}...")
    projects, regions = load_projects(KB_PATH)
    kb_hash = compute_kb_hash(KB_PATH)
    
    print(f"Found {len(projects)} projects and {len(regions)} regions.")
    
    leads = []
    
    print(f"Generating {TARGET_LEAD_COUNT} synthetic leads...")
    
    for i in range(TARGET_LEAD_COUNT):
        # 1. Basic Info
        first_name = random.choice(NAMES_FIRST)
        last_name = random.choice(NAMES_LAST)
        full_name = f"{first_name} {last_name}"
        phone = generate_phone()
        source = random.choice(SOURCES)
        
        # 2. Project & Region Preference
        # Pick a random project to be the "Interest"
        project = random.choice(projects)
        interest_project = project['project_name']
        region = project.get('region', random.choice(regions))
        
        # 3. Unit & Budget
        # Try to parse unit types from JSON if possible, else random
        try:
            p_units = json.loads(project.get('unit_types_offered_json', '[]'))
            if not p_units:
                 p_units = UNIT_TYPES
        except:
             p_units = UNIT_TYPES
             
        unit_type = random.choice(p_units) if p_units else random.choice(UNIT_TYPES)
        
        # Budget logic - try to be realistic based on project price
        try:
            start_price = float(project.get('starting_price_value', 0))
        except:
            start_price = 0
            
        if start_price > 0:
            min_b = start_price * random.uniform(0.8, 1.2)
            max_b = min_b * random.uniform(1.2, 1.5)
        else:
            # Fallback defaults
            min_b = random.randint(1, 10) * 1_000_000
            max_b = min_b + random.randint(1, 5) * 1_000_000

        budget_min = int(min_b)
        budget_max = int(max_b)

        # 4. Sales Journey Info
        purpose = random.choice(PURPOSES)
        timeline = random.choice(TIMELINES)
        next_step = random.choice(NEXT_STEPS)
        
        # 5. Lead Summary & Tags
        summary = f"Client interested in {unit_type} in {region}. Budget around {budget_max/1000000:.1f}M. {purpose} purpose. Timeline: {timeline}."
        
        tags = [region, purpose, timeline]
        if "High" in project.get('brand_family', ''): tags.append("High Value")
        tags_str = format_tags(tags)
        
        # 6. Timestamps
        created_at = datetime.datetime.now().isoformat()
        
        leads.append({
            "id": i + 1,
            "uuid": str(uuid.uuid4()),
            "name": full_name,
            "phone": phone,
            "source": source,
            "interest_projects": interest_project,
            "preferred_region": region,
            "unit_type": unit_type,
            "budget_min": budget_min,
            "budget_max": budget_max,
            "purpose": purpose,
            "timeline": timeline,
            "next_step": next_step,
            "lead_summary": summary,
            "tags": tags_str,
            "kb_version_hash": kb_hash,
            "created_at": created_at
        })

    # Ensure output directory exists
    os.makedirs(os.path.dirname(LEADS_OUTPUT_PATH), exist_ok=True)
    
    # Write to CSV
    fieldnames = ["id", "uuid", "name", "phone", "source", "interest_projects", "preferred_region", 
                  "unit_type", "budget_min", "budget_max", "purpose", "timeline", "next_step", 
                  "lead_summary", "tags", "kb_version_hash", "created_at"]
    
    with open(LEADS_OUTPUT_PATH, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(leads)
        
    print(f"Successfully generated {len(leads)} leads to {LEADS_OUTPUT_PATH}")
    
    # Stats Report
    print("\n--- Generation Stats ---")
    print(f"Total Leads: {len(leads)}")
    
    region_counts = {}
    for l in leads:
        r = l['preferred_region']
        region_counts[r] = region_counts.get(r, 0) + 1
    
    print("Region Distribution:")
    for r, c in region_counts.items():
        print(f"  - {r}: {c}")

if __name__ == "__main__":
    generate_leads()
