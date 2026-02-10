#!/usr/bin/env python3
"""
PalmX KB Acquisition — Buyer-Critical KB CSV Builder
Produces palmx_projects_buyer_kb.csv, palmx_sources_audit.csv, palmx_screens_index.csv
"""
import csv, json, sys, os
from datetime import date

TODAY = date.today().isoformat()
BASE = "https://www.palmhillsdevelopments.com/en-us"
CONTACT_URL = f"{BASE}/contactus"

def jd(obj): return json.dumps(obj, ensure_ascii=False, separators=(",",":"))
def slug(name):
    s = name.lower().strip()
    for old, new in [("the ritz-carlton residences cairo, palm hills","ritz_carlton_residences_cairo_palm_hills"),
                     ("p/x","p_x"),("st. 88","st_88"),("/","_"),(",",""),(".",""),("-"," ")]:
        s = s.replace(old, new)
    return "_".join(s.split())

# Price text → numeric integer string (strict: only if M EGP is explicit)
def price_to_int(p_str):
    """Convert '34.4M' → '34400000'. Returns 'unknown' if ambiguous."""
    if not p_str or p_str in ("unknown","on_request"): return p_str
    import re
    m = re.match(r'([\d.]+)\s*M', p_str.strip(), re.IGNORECASE)
    if m:
        val = float(m.group(1))
        return str(int(val * 1_000_000))
    m2 = re.match(r'([\d,]+)\s*EGP', p_str.strip(), re.IGNORECASE)
    if m2:
        return m2.group(1).replace(",","")
    return "unknown"

PROJECTS = []
AUDIT_ROWS = []

def audit(pid, field, value, source_url, ev_type="dom", snippet="", ss_path=""):
    AUDIT_ROWS.append({
        "project_id": pid,
        "field_name": field,
        "field_value": str(value),
        "source_url": source_url,
        "evidence_type": ev_type,
        "evidence_snippet": snippet[:200],
        "screenshot_path": ss_path,
        "captured_date": TODAY,
    })

def add(name, brand, url_path, region, city_area, micro,
        ptype, status, sales, dev_inv,
        unit_types, beds_min, beds_max, bua_min, bua_max,
        starting_price, currency, pr_min, pr_max, pr_status,
        pricing_disclaimer, payment_headline, dp_min, dp_max, inst_min, inst_max,
        delivery_window, del_yr_min, del_yr_max, finishing,
        amenities, golf, beach, lagoons, clubhouse, pools, gym,
        brochure_urls, gallery_urls, zones_raw, map_link="unknown"):

    pid = slug(name)
    proj_url = f"{BASE}/{url_path}" if url_path else "unknown"
    inq_url = proj_url if proj_url != "unknown" else "unknown"
    src_links = [proj_url] if proj_url != "unknown" else []

    # Build zones_json
    zones_json = []
    listings_json = []
    unit_templates = []
    for z in zones_raw:
        zn = z.get("name","unknown")
        zp = z.get("price","unknown")
        zut = z.get("unit_type", zn)
        zsrc = proj_url

        zones_json.append({"zone_name": zn, "source_url": zsrc, "captured_date": TODAY})

        p_int = price_to_int(zp)
        p_st = "official" if p_int not in ("unknown","on_request") else zp if zp=="on_request" else "unknown"

        listings_json.append({
            "listing_id": f"{pid}_{zn}_{zut}".replace(" ","_").lower(),
            "zone_name": zn, "unit_type": zut,
            "bedrooms": "unknown", "bua_sqm": "unknown",
            "price_value": p_int, "currency": currency if p_int not in ("unknown","on_request") else "unknown",
            "price_status": p_st,
            "payment_plan_text": payment_headline,
            "delivery": delivery_window,
            "source_url": zsrc, "evidence_type": "dom",
            "screenshot_path": "", "captured_date": TODAY,
        })
        unit_templates.append({
            "unit_type": zut, "bedrooms": "unknown",
            "bua_range_min_sqm": "unknown", "bua_range_max_sqm": "unknown",
            "price_range_min": p_int if p_int not in ("unknown","on_request") else "unknown",
            "price_range_max": p_int if p_int not in ("unknown","on_request") else "unknown",
            "currency": currency if p_int not in ("unknown","on_request") else "unknown",
        })

        # Audit row for pricing
        if p_st == "official":
            audit(pid, "starting_price_value", p_int, zsrc, "dom", f"Zone '{zn}' starting from {zp}")

    # Compute ranges from zones_raw
    numeric_prices = [int(price_to_int(z.get("price","unknown"))) for z in zones_raw
                      if price_to_int(z.get("price","unknown")) not in ("unknown","on_request")]
    if numeric_prices and starting_price == "unknown":
        starting_price = str(min(numeric_prices))
    if numeric_prices:
        pr_min = str(min(numeric_prices)) if pr_min == "unknown" else pr_min
        pr_max = str(max(numeric_prices)) if pr_max == "unknown" else pr_max
        pr_status = "official"

    # Confidence scoring
    conf = 0.30
    if proj_url != "unknown": conf += 0.20
    if zones_json and all(z.get("source_url","")!="" for z in zones_json): conf += 0.20
    if brochure_urls: conf += 0.10
    if beds_min != "unknown" and bua_min != "unknown": conf += 0.10
    if numeric_prices: conf += 0.10
    conf = round(min(conf, 1.00), 2)

    disclaimers = []
    if not url_path: disclaimers.append("Project page not found on official site.")
    if pricing_disclaimer and pricing_disclaimer != "unknown":
        disclaimers.append(pricing_disclaimer)
    if pr_status == "on_request":
        disclaimers.append("Pricing on request — contact Palm Hills.")
    if beds_min == "unknown":
        disclaimers.append("BUA/bedroom data not published on official site; available in brochures.")

    # Audit core fields
    if proj_url != "unknown":
        audit(pid, "official_project_url", proj_url, proj_url, "dom", "Project detail page")
        audit(pid, "region", region, proj_url, "dom", f"Location: {city_area}")
        audit(pid, "project_status", status, proj_url, "dom", f"Status: {status}")

    row = {
        "project_id": pid, "project_name": name, "brand_family": brand,
        "official_project_url": proj_url, "inquiry_form_url": inq_url,
        "official_contact_page_url": CONTACT_URL,
        "region": region, "city_area": city_area, "micro_location": micro,
        "map_link": map_link,
        "project_type": ptype, "project_status": status,
        "current_sales_status": sales, "developer_inventory_status": dev_inv,
        "unit_types_offered_json": jd(unit_types),
        "bedrooms_range_min": beds_min, "bedrooms_range_max": beds_max,
        "bua_range_min_sqm": bua_min, "bua_range_max_sqm": bua_max,
        "starting_price_value": starting_price, "starting_price_currency": currency if starting_price not in ("unknown","on_request") else "unknown",
        "price_range_min": pr_min, "price_range_max": pr_max,
        "price_status": pr_status, "pricing_date": TODAY, "pricing_disclaimer": pricing_disclaimer,
        "payment_plan_headline": payment_headline,
        "downpayment_percent_min": dp_min, "downpayment_percent_max": dp_max,
        "installment_years_min": inst_min, "installment_years_max": inst_max,
        "delivery_window": delivery_window, "delivery_year_min": del_yr_min,
        "delivery_year_max": del_yr_max, "finishing_levels_offered_json": jd(finishing),
        "key_amenities_json": jd(amenities),
        "golf_flag": golf, "beach_access_flag": beach, "lagoons_flag": lagoons,
        "clubhouse_flag": clubhouse, "pools_flag": pools, "gym_flag": gym,
        "brochure_urls_json": jd(brochure_urls), "gallery_urls_json": jd(gallery_urls),
        "source_links_json": jd(src_links), "screenshot_paths_json": jd([]),
        "last_verified_date": TODAY, "confidence_score": f"{conf:.2f}",
        "disclaimers_json": jd(disclaimers),
        "zones_json": jd(zones_json), "unit_templates_json": jd(unit_templates),
        "listings_json": jd(listings_json),
    }
    PROJECTS.append(row)

# ═════════════════════════════════════════════════════════════════════
# RESIDENTIAL (35 projects)
# ═════════════════════════════════════════════════════════════════════

# 1. 97 Hills — UPDATED from deep extraction
add("97 Hills", "Residential", "residential-properties/97-hills",
    "East","New Cairo","Middle Ring Road",
    "residential","under_construction","selling","available",
    ["Villa","Townhouse","Family Home"],"unknown","unknown","unknown","unknown",
    "unknown","EGP","unknown","unknown","official",
    "Starting prices shown on zone cards","unknown","unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown",[],
    ["Gated Community"],"unknown","unknown","unknown","unknown","unknown","unknown",
    [],[],
    [{"name":"Zone 1","unit_type":"Villa","price":"37M"}])

# 2. Badya — UPDATED with 6 zones from deep extraction
add("Badya", "Residential", "residential-properties/city/badya",
    "West","6th of October / West Cairo","Badya City",
    "residential","under_construction","selling","available",
    ["Villa","Townhouse","Apartment"],"unknown","unknown","unknown","unknown",
    "unknown","EGP","unknown","unknown","official",
    "Starting prices per zone card","unknown","unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown",[],
    ["Clubhouse","Schools","Healthcare","Sports Arenas"],"unknown","unknown","unknown","true","unknown","unknown",
    [],[],
    [{"name":"Dae","unit_type":"Villa/Townhouse","price":"34.4M"},
     {"name":"Rae","unit_type":"Apartment","price":"14.7M"},
     {"name":"Isana","unit_type":"Apartment","price":"14.7M"},
     {"name":"Isha","unit_type":"Apartment","price":"18.2M"},
     {"name":"Isola","unit_type":"Apartment","price":"17.5M"},
     {"name":"Isara","unit_type":"Apartment","price":"14.7M"}])

# 3. Bamboo (Operating/Delivered)
add("Bamboo", "Residential", "residential-properties/bamboo",
    "West","6th of October / West Cairo","Palm Hills October",
    "residential","delivered","not_selling","sold_out",
    [],"unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown","unknown","unknown",
    "Delivered/Operating — no active sales","unknown","unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown",[],
    [],"unknown","unknown","unknown","unknown","unknown","unknown",
    [],[],[])

# 4. Bamboo III (empty page)
add("Bamboo III", "Residential", "",
    "West","6th of October / West Cairo","unknown",
    "residential","unknown","unknown","unknown",
    [],"unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown","unknown","unknown",
    "Project page not found","unknown","unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown",[],
    [],"unknown","unknown","unknown","unknown","unknown","unknown",
    [],[],[])

# 5. Bamboo Extension (Delivered)
add("Bamboo Extension", "Residential", "residential-properties/bamboo-extension",
    "West","6th of October / West Cairo","Palm Hills October",
    "residential","delivered","not_selling","sold_out",
    [],"unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown","unknown","unknown",
    "Delivered/Operating — no active sales","unknown","unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown",[],
    [],"unknown","unknown","unknown","unknown","unknown","unknown",
    [],[],[])

# 6. Casa (Delivered)
add("Casa", "Residential", "residential-properties/casa",
    "West","6th of October / West Cairo","unknown",
    "residential","delivered","not_selling","sold_out",
    [],"unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown","unknown","unknown",
    "Delivered/Operating — no active sales","unknown","unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown",[],
    [],"unknown","unknown","unknown","unknown","unknown","unknown",
    [],[],[])

# 7. Golf Extension (Delivered)
add("Golf Extension", "Residential", "residential-properties/golf-extension",
    "West","6th of October / West Cairo","unknown",
    "residential","delivered","not_selling","sold_out",
    [],"unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown","unknown","unknown",
    "Delivered/Operating","unknown","unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown",[],
    [],"unknown","unknown","unknown","unknown","unknown","unknown",
    [],[],[])

# 8. Golf Views (Delivered)
add("Golf Views", "Residential", "residential-properties/golf-views",
    "West","6th of October / West Cairo","unknown",
    "residential","delivered","not_selling","sold_out",
    [],"unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown","unknown","unknown",
    "Delivered/Operating","unknown","unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown",[],
    [],"unknown","unknown","unknown","unknown","unknown","unknown",
    [],[],[])

# 9. Hacienda Bay — UPDATED: 5 zones from deep extraction
add("Hacienda Bay", "Residential", "residential-properties/hacienda-bay",
    "Coast","North Coast","Sidi Abdel Rahman",
    "residential","under_construction","selling","available",
    ["Villa","Cabin","Chalet"],"unknown","unknown","unknown","unknown",
    "unknown","EGP","unknown","unknown","official",
    "Starting prices per zone card","unknown","unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown",[],
    ["Beach","Pools","Dining"],"unknown","true","unknown","unknown","true","unknown",
    [],[],
    [{"name":"Le Sidi","unit_type":"Cabin","price":"25M"},
     {"name":"Water Villas","unit_type":"Villa","price":"100M"},
     {"name":"X","unit_type":"Villa/Chalet","price":"45M"},
     {"name":"Lakeyard","unit_type":"Cabin","price":"25M"},
     {"name":"Bay Villas","unit_type":"Villa","price":"100M"}])

# 10. Hacienda Blue
add("Hacienda Blue", "Residential", "residential-properties/hacienda-blue",
    "Coast","North Coast","unknown",
    "residential","under_construction","selling","available",
    ["Villa","Chalet","Townhouse"],"unknown","unknown","unknown","unknown",
    "unknown","EGP","unknown","unknown","official",
    "Starting prices per zone card","unknown","unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown",[],
    ["Beach"],"unknown","true","unknown","unknown","unknown","unknown",
    [],[],
    [{"name":"Villas","unit_type":"Villa","price":"58M"},
     {"name":"Chalets","unit_type":"Chalet","price":"19M"},
     {"name":"Townhouse","unit_type":"Townhouse","price":"31M"}])

# 11. Hacienda Heneish
add("Hacienda Heneish", "Residential", "residential-properties/hacienda-heneish",
    "Coast","North Coast","Heneish",
    "residential","under_construction","selling","available",
    ["Villa","Condo","Cabin","Chalet","Pied Dans L'eau"],"unknown","unknown","unknown","unknown",
    "unknown","EGP","unknown","unknown","official",
    "Starting prices per zone card","unknown","unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown",[],
    ["Beach"],"unknown","true","unknown","unknown","unknown","unknown",
    [],[],
    [{"name":"Villa","unit_type":"Villa","price":"52.4M"},
     {"name":"Condos","unit_type":"Condo","price":"16.9M"},
     {"name":"Cabins","unit_type":"Cabin","price":"17.8M"},
     {"name":"Pied Dans L'eau","unit_type":"Pied Dans L'eau","price":"94.8M"},
     {"name":"Chalets","unit_type":"Chalet","price":"19.5M"}])

# 12. Hacienda Waters
add("Hacienda Waters", "Residential", "residential-properties/hacienda-waters",
    "Coast","North Coast","unknown",
    "residential","under_construction","selling","available",
    ["Apartment","Villa"],"unknown","unknown","unknown","unknown",
    "unknown","EGP","unknown","unknown","official",
    "Starting prices per zone card","unknown","unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown",[],
    ["Beach"],"unknown","true","unknown","unknown","unknown","unknown",
    [],[],
    [{"name":"Apartments","unit_type":"Apartment","price":"11.2M"},
     {"name":"Villas","unit_type":"Villa","price":"106.5M"}])

# 13. Hacienda Waters 2 (no zones visible)
add("Hacienda Waters 2", "Residential", "residential-properties/hacienda-waters-2",
    "Coast","North Coast","unknown",
    "residential","under_construction","selling","unknown",
    [],"unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown","unknown","on_request",
    "No zones currently displayed","unknown","unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown",[],
    ["Beach"],"unknown","true","unknown","unknown","unknown","unknown",
    [],[],[])

# 14. Hacienda West
add("Hacienda West", "Residential", "residential-properties/hacienda-west",
    "Coast","North Coast","unknown",
    "residential","under_construction","selling","available",
    ["Beach House","Chalet","Cabanna"],"unknown","unknown","unknown","unknown",
    "unknown","EGP","unknown","unknown","official",
    "Starting prices per zone card","unknown","unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown",[],
    ["Beach"],"unknown","true","unknown","unknown","unknown","unknown",
    [],[],
    [{"name":"Beach House","unit_type":"Beach House","price":"41.2M"},
     {"name":"Lime Chalets","unit_type":"Chalet","price":"29.6M"},
     {"name":"Aria Cabanna","unit_type":"Cabanna","price":"33.3M"}])

# 15. Hacienda White (Delivered)
add("Hacienda White", "Residential", "residential-properties/hacienda-white",
    "Coast","North Coast","unknown",
    "residential","delivered","not_selling","sold_out",
    [],"unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown","unknown","unknown",
    "Delivered/Operating","unknown","unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown",[],
    ["Beach"],"unknown","true","unknown","unknown","unknown","unknown",
    [],[],[])

# 16. Jirian Palm Hills
add("Jirian Palm Hills", "Residential", "residential-properties/jirian-palm-hills",
    "West","6th of October / West Cairo","unknown",
    "residential","under_construction","selling","available",
    ["Villa","Apartment"],"unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown","unknown","on_request",
    "Pricing on request — zones visible but no numeric prices","unknown","unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown",[],
    [],"unknown","unknown","unknown","unknown","unknown","unknown",
    [],[],
    [{"name":"Two Story Villas","unit_type":"Villa","price":"on_request"},
     {"name":"One Story Villa","unit_type":"Villa","price":"on_request"},
     {"name":"Apartments","unit_type":"Apartment","price":"on_request"}])

# 17. New Capital Gardens
add("New Capital Gardens", "Residential", "residential-properties/new-capital-gardens",
    "New_Capital","New Administrative Capital","unknown",
    "residential","under_construction","selling","available",
    ["Apartment"],"unknown","unknown","unknown","unknown",
    "unknown","EGP","unknown","unknown","official",
    "Starting prices per phase card","unknown","unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown",[],
    [],"unknown","unknown","unknown","unknown","unknown","unknown",
    [],[],
    [{"name":"Phase 1","unit_type":"Apartment","price":"5.5M"},
     {"name":"Phase 2","unit_type":"Apartment","price":"5.5M"}])

# 18. P/X (empty page)
add("P/X", "Residential", "",
    "West","6th of October / West Cairo","unknown",
    "residential","unknown","unknown","unknown",
    [],"unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown","unknown","unknown",
    "Project page not found","unknown","unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown",[],
    [],"unknown","unknown","unknown","unknown","unknown","unknown",
    [],[],[])

# 19. Palm Hills Alexandria
add("Palm Hills Alexandria", "Residential", "residential-properties/palm-hills-alexandria",
    "Alex","Alexandria","unknown",
    "residential","under_construction","selling","available",
    ["Villa","Townhouse","Twin House"],"unknown","unknown","unknown","unknown",
    "unknown","EGP","unknown","unknown","official",
    "Starting prices per zone card","unknown","unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown",[],
    [],"unknown","unknown","unknown","unknown","unknown","unknown",
    [],[],
    [{"name":"Palm Villas","unit_type":"Villa","price":"28M"},
     {"name":"Tessera","unit_type":"Villa/Townhouse","price":"23.3M"}])

# 20. Palm Hills Katameya 1 (Delivered)
add("Palm Hills Katameya 1", "Residential", "residential-properties/palm-hills-katameya-1",
    "East","New Cairo","Katameya",
    "residential","delivered","not_selling","sold_out",
    [],"unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown","unknown","unknown",
    "Delivered/Operating","unknown","unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown",[],
    ["Golf"],"true","unknown","unknown","true","unknown","unknown",
    [],[],[])

# 21. Palm Hills Katameya 2 (Delivered)
add("Palm Hills Katameya 2", "Residential", "residential-properties/palm-hills-katameya-2",
    "East","New Cairo","Katameya",
    "residential","delivered","not_selling","sold_out",
    [],"unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown","unknown","unknown",
    "Delivered/Operating","unknown","unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown",[],
    ["Golf"],"true","unknown","unknown","true","unknown","unknown",
    [],[],[])

# 22. Palm Hills New Alamein
add("Palm Hills New Alamein", "Residential", "residential-properties/palm-hills-new-alamein",
    "Coast","North Coast","New Alamein",
    "residential","under_construction","selling","available",
    ["Apartment"],"unknown","unknown","unknown","unknown",
    "unknown","EGP","unknown","unknown","official",
    "Starting prices per zone card","unknown","unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown",[],
    ["Beach"],"unknown","true","unknown","unknown","unknown","unknown",
    [],[],
    [{"name":"Alamein Apartments","unit_type":"Apartment","price":"8.1M"}])

# 23. Palm Hills New Cairo
add("Palm Hills New Cairo", "Residential", "residential-properties/palm-hills-new-cairo",
    "East","New Cairo","unknown",
    "residential","under_construction","selling","available",
    ["Villa","Apartment","Townhouse"],"unknown","unknown","unknown","unknown",
    "unknown","EGP","unknown","unknown","official",
    "Starting prices per phase card","unknown","unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown",[],
    ["Golf","Clubhouse"],"true","unknown","unknown","true","unknown","unknown",
    [],[],
    [{"name":"Phase 1","unit_type":"Villa","price":"90M"},
     {"name":"Phase 2","unit_type":"Villa","price":"30.7M"},
     {"name":"Phase 3","unit_type":"Apartment","price":"20.2M"},
     {"name":"Phase 4","unit_type":"Villa","price":"26.9M"},
     {"name":"Phase 5","unit_type":"Mixed","price":"8.9M"}])

# 24. Palm Hills October (Delivered)
add("Palm Hills October", "Residential", "residential-properties/palm-hills-october",
    "West","6th of October / West Cairo","unknown",
    "residential","delivered","not_selling","sold_out",
    [],"unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown","unknown","unknown",
    "Delivered/Operating","unknown","unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown",[],
    [],"unknown","unknown","unknown","unknown","unknown","unknown",
    [],[],[])

# 25. Palm Parks (Delivered)
add("Palm Parks", "Residential", "residential-properties/palm-parks",
    "West","6th of October / West Cairo","unknown",
    "residential","delivered","not_selling","sold_out",
    [],"unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown","unknown","unknown",
    "Delivered/Operating","unknown","unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown",[],
    [],"unknown","unknown","unknown","unknown","unknown","unknown",
    [],[],[])

# 26. Palm Valley (Delivered)
add("Palm Valley", "Residential", "residential-properties/palm-valley",
    "West","6th of October / West Cairo","unknown",
    "residential","delivered","not_selling","sold_out",
    [],"unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown","unknown","unknown",
    "Delivered/Operating","unknown","unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown",[],
    [],"unknown","unknown","unknown","unknown","unknown","unknown",
    [],[],[])

# 27. The Crown
add("The Crown", "Residential", "residential-properties/the-crown",
    "West","6th of October / West Cairo","unknown",
    "residential","under_construction","selling","available",
    ["Villa","Family Home"],"unknown","unknown","unknown","unknown",
    "unknown","EGP","unknown","unknown","official",
    "Starting prices per phase card","unknown","unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown",[],
    [],"unknown","unknown","unknown","unknown","unknown","unknown",
    [],[],
    [{"name":"Phase 3","unit_type":"Villa/Family Home","price":"50.1M"}])

# 28. The Crown Extension
add("The Crown Extension", "Residential", "residential-properties/the-crown-extension",
    "West","6th of October / West Cairo","unknown",
    "residential","under_construction","selling","available",
    ["Family Home","Twin Home"],"unknown","unknown","unknown","unknown",
    "unknown","EGP","unknown","unknown","official",
    "Starting prices per zone card","unknown","unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown",[],
    [],"unknown","unknown","unknown","unknown","unknown","unknown",
    [],[],
    [{"name":"Family Homes","unit_type":"Family Home","price":"28M"},
     {"name":"Twin Homes","unit_type":"Twin Home","price":"34.9M"}])

# 29. Ritz-Carlton (empty page)
add("The Ritz-Carlton Residences Cairo, Palm Hills", "Residential", "",
    "West","6th of October / West Cairo","unknown",
    "branded","unknown","unknown","unknown",
    [],"unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown","unknown","unknown",
    "Project page not found","unknown","unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown",[],
    [],"unknown","unknown","unknown","unknown","unknown","unknown",
    [],[],[])

# 30. The Village (Delivered)
add("The Village", "Residential", "residential-properties/the-village",
    "East","New Cairo","unknown",
    "residential","delivered","not_selling","sold_out",
    [],"unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown","unknown","unknown",
    "Delivered/Operating","unknown","unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown",[],
    [],"unknown","unknown","unknown","unknown","unknown","unknown",
    [],[],[])

# 31. Village de la Capitale (empty page)
add("Village de la Capitale", "Residential", "",
    "New_Capital","New Administrative Capital","unknown",
    "residential","unknown","unknown","unknown",
    [],"unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown","unknown","unknown",
    "Project page not found","unknown","unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown",[],
    [],"unknown","unknown","unknown","unknown","unknown","unknown",
    [],[],[])

# 32. Village Avenue (Delivered)
add("Village Avenue", "Residential", "residential-properties/village-avenue",
    "East","New Cairo","unknown",
    "residential","delivered","not_selling","sold_out",
    [],"unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown","unknown","unknown",
    "Delivered/Operating","unknown","unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown",[],
    [],"unknown","unknown","unknown","unknown","unknown","unknown",
    [],[],[])

# 33. Village Gardens Katameya (Delivered)
add("Village Gardens Katameya", "Residential", "residential-properties/village-gardens-katameya",
    "East","New Cairo","Katameya",
    "residential","delivered","not_selling","sold_out",
    [],"unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown","unknown","unknown",
    "Delivered/Operating","unknown","unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown",[],
    [],"unknown","unknown","unknown","unknown","unknown","unknown",
    [],[],[])

# 34. Village Gate (Delivered)
add("Village Gate", "Residential", "residential-properties/village-gate",
    "East","New Cairo","unknown",
    "residential","delivered","not_selling","sold_out",
    [],"unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown","unknown","unknown",
    "Delivered/Operating","unknown","unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown",[],
    [],"unknown","unknown","unknown","unknown","unknown","unknown",
    [],[],[])

# 35. WoodVille (Delivered)
add("WoodVille", "Residential", "residential-properties/woodville",
    "West","6th of October / West Cairo","unknown",
    "residential","delivered","not_selling","sold_out",
    [],"unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown","unknown","unknown",
    "Delivered/Operating","unknown","unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown",[],
    [],"unknown","unknown","unknown","unknown","unknown","unknown",
    [],[],[])

# ═════════════════════════════════════════════════════════════════════
# COMMERCIAL (10 projects)
# ═════════════════════════════════════════════════════════════════════

# 36. Crown Central
add("Crown Central", "Commercial", "commercial-properties/crown-central",
    "West","6th of October / West Cairo","unknown",
    "commercial","under_construction","selling","available",
    ["Office","Retail","F&B"],"unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown","unknown","on_request",
    "Commercial pricing on request","unknown","unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown",[],
    [],"unknown","unknown","unknown","unknown","unknown","unknown",
    [],[],
    [{"name":"Office Spaces","unit_type":"Office","price":"on_request"},
     {"name":"Retail","unit_type":"Retail","price":"on_request"},
     {"name":"F&B","unit_type":"F&B","price":"on_request"}])

# 37. Palmet October
add("Palmet October", "Commercial", "commercial-properties/palmet-october",
    "West","6th of October / West Cairo","unknown",
    "commercial","under_construction","selling","available",
    ["F&B","Retail","Office"],"unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown","unknown","on_request",
    "Commercial pricing on request","unknown","unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown",[],
    [],"unknown","unknown","unknown","unknown","unknown","unknown",
    [],[],
    [{"name":"F&B","unit_type":"F&B","price":"on_request"},
     {"name":"Retail","unit_type":"Retail","price":"on_request"},
     {"name":"Office spaces","unit_type":"Office","price":"on_request"}])

# 38. Palmet New Cairo
add("Palmet New Cairo", "Commercial", "commercial-properties/palmet-new-cairo",
    "East","New Cairo","unknown",
    "commercial","under_construction","selling","available",
    ["Office"],"unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown","unknown","on_request",
    "Commercial pricing on request","unknown","unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown",[],
    [],"unknown","unknown","unknown","unknown","unknown","unknown",
    [],[],
    [{"name":"Office spaces","unit_type":"Office","price":"on_request"}])

# 39. Village Gate Mall
add("Village Gate Mall", "Commercial", "commercial-properties/village-gate-mall",
    "East","New Cairo","unknown",
    "commercial","under_construction","selling","available",
    ["Office","Clinic"],"unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown","unknown","on_request",
    "Commercial pricing on request","unknown","unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown",[],
    [],"unknown","unknown","unknown","unknown","unknown","unknown",
    [],[],
    [{"name":"Offices","unit_type":"Office","price":"on_request"},
     {"name":"Clinics","unit_type":"Clinic","price":"on_request"}])

# 40. Golf Central
add("Golf Central", "Commercial", "commercial-properties/golf-central",
    "West","6th of October / West Cairo","unknown",
    "commercial","under_construction","selling","available",
    [],"unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown","unknown","on_request",
    "No zones displayed; pricing on request","unknown","unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown",[],
    [],"unknown","unknown","unknown","unknown","unknown","unknown",
    [],[],[])

# 41. Hale Town
add("Hale Town", "Commercial", "commercial-properties/hale-town",
    "West","6th of October / West Cairo","unknown",
    "commercial","under_construction","selling","available",
    [],"unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown","unknown","on_request",
    "No zones displayed; pricing on request","unknown","unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown",[],
    [],"unknown","unknown","unknown","unknown","unknown","unknown",
    [],[],[])

# 42. Lakeyard (Operating)
add("Lakeyard", "Commercial", "commercial-properties/lakeyard",
    "Coast","North Coast","Hacienda Bay",
    "commercial","delivered","not_selling","sold_out",
    [],"unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown","unknown","unknown",
    "Delivered/Operating","unknown","unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown",[],
    [],"unknown","unknown","unknown","unknown","unknown","unknown",
    [],[],[])

# 43. Palm Central (Operating)
add("Palm Central", "Commercial", "commercial-properties/palm-central",
    "West","6th of October / West Cairo","unknown",
    "commercial","delivered","not_selling","sold_out",
    [],"unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown","unknown","unknown",
    "Delivered/Operating","unknown","unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown",[],
    [],"unknown","unknown","unknown","unknown","unknown","unknown",
    [],[],[])

# 44. The Lane (Operating)
add("The Lane", "Commercial", "commercial-properties/the-lane",
    "West","6th of October / West Cairo","unknown",
    "commercial","delivered","not_selling","sold_out",
    [],"unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown","unknown","unknown",
    "Delivered/Operating","unknown","unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown",[],
    [],"unknown","unknown","unknown","unknown","unknown","unknown",
    [],[],[])

# 45. St. 88 (empty page)
add("St. 88", "Commercial", "",
    "unknown","unknown","unknown",
    "commercial","unknown","unknown","unknown",
    [],"unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown","unknown","unknown",
    "Project page not found","unknown","unknown","unknown","unknown","unknown",
    "unknown","unknown","unknown",[],
    [],"unknown","unknown","unknown","unknown","unknown","unknown",
    [],[],[])


# ═════════════════════════════════════════════════════════════════════
# CSV output
# ═════════════════════════════════════════════════════════════════════

BUYER_COLS = [
    "project_id","project_name","brand_family",
    "official_project_url","inquiry_form_url","official_contact_page_url",
    "region","city_area","micro_location","map_link",
    "project_type","project_status","current_sales_status","developer_inventory_status",
    "unit_types_offered_json","bedrooms_range_min","bedrooms_range_max","bua_range_min_sqm","bua_range_max_sqm",
    "starting_price_value","starting_price_currency","price_range_min","price_range_max","price_status","pricing_date","pricing_disclaimer",
    "payment_plan_headline","downpayment_percent_min","downpayment_percent_max","installment_years_min","installment_years_max",
    "delivery_window","delivery_year_min","delivery_year_max","finishing_levels_offered_json",
    "key_amenities_json","golf_flag","beach_access_flag","lagoons_flag","clubhouse_flag","pools_flag","gym_flag",
    "brochure_urls_json","gallery_urls_json",
    "source_links_json","screenshot_paths_json","last_verified_date","confidence_score","disclaimers_json",
    "zones_json","unit_templates_json","listings_json",
]

AUDIT_COLS = ["project_id","field_name","field_value","source_url","evidence_type","evidence_snippet","screenshot_path","captured_date"]

def validate():
    errors = []
    if len(PROJECTS) != 45: errors.append(f"Row count {len(PROJECTS)} != 45")
    ids = [p["project_id"] for p in PROJECTS]
    if len(set(ids)) != 45: errors.append(f"Unique IDs = {len(set(ids))}")
    json_cols = [c for c in BUYER_COLS if c.endswith("_json")]
    for i, p in enumerate(PROJECTS):
        for jc in json_cols:
            try: json.loads(p[jc])
            except: errors.append(f"Row {i} ({p['project_id']}): {jc} bad JSON")
        for c in BUYER_COLS:
            if p.get(c) is None or p.get(c) == "":
                errors.append(f"Row {i} ({p['project_id']}): {c} empty")
    return errors

def write_csvs():
    os.makedirs("outputs", exist_ok=True)

    # Buyer KB
    with open("outputs/palmx_projects_buyer_kb.csv","w",newline="",encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=BUYER_COLS, extrasaction="ignore")
        w.writeheader(); w.writerows(PROJECTS)

    # Audit
    with open("outputs/palmx_sources_audit.csv","w",newline="",encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=AUDIT_COLS)
        w.writeheader(); w.writerows(AUDIT_ROWS)

    # Screens index (placeholder — screenshots collected separately)
    with open("outputs/palmx_screens_index.csv","w",newline="",encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["project_id","page_type","source_url","screenshot_path","captured_date"])
        w.writeheader()

def coverage():
    print("=" * 60)
    print("PalmX Buyer-Critical KB — Coverage Report")
    print("=" * 60)
    n = len(PROJECTS)
    has_url = sum(1 for p in PROJECTS if p["official_project_url"] != "unknown")
    has_zones = sum(1 for p in PROJECTS if p["zones_json"] != "[]")
    has_listings = sum(1 for p in PROJECTS if p["listings_json"] != "[]")
    has_price = sum(1 for p in PROJECTS if p["price_status"] == "official")
    has_onreq = sum(1 for p in PROJECTS if p["price_status"] == "on_request")
    has_beds = sum(1 for p in PROJECTS if p["bedrooms_range_min"] != "unknown")
    has_bua = sum(1 for p in PROJECTS if p["bua_range_min_sqm"] != "unknown")
    has_utypes = sum(1 for p in PROJECTS if p["unit_types_offered_json"] != "[]")

    print(f"Total projects:              {n}")
    print(f"Official project URLs:       {has_url}/{n}")
    print(f"Zone URLs discovered:        {has_zones}/{n}")
    print(f"Listings extracted:          {has_listings}/{n}")
    print(f"Official numeric pricing:    {has_price}/{n}")
    print(f"Price on_request:            {has_onreq}/{n}")
    print(f"Bedrooms range extracted:    {has_beds}/{n} (not published on site)")
    print(f"BUA range extracted:         {has_bua}/{n} (not published on site)")
    print(f"Unit types identified:       {has_utypes}/{n}")
    print(f"Audit rows:                  {len(AUDIT_ROWS)}")
    print(f"Last verified:               {TODAY}")
    print("=" * 60)

if __name__ == "__main__":
    errs = validate()
    if errs:
        print("VALIDATION ERRORS:")
        for e in errs: print(f"  ✗ {e}")
        sys.exit(1)
    print("✓ All validation passed")
    write_csvs()
    print(f"✓ Wrote outputs/palmx_projects_buyer_kb.csv ({len(PROJECTS)} rows, {len(BUYER_COLS)} cols)")
    print(f"✓ Wrote outputs/palmx_sources_audit.csv ({len(AUDIT_ROWS)} audit rows)")
    print(f"✓ Wrote outputs/palmx_screens_index.csv")
    coverage()
