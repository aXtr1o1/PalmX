#!/usr/bin/env python3
"""
PalmX KB Acquisition — Master CSV Builder
Assembles extracted Palm Hills project data into palmx_projects_master.csv
"""

import csv
import json
import sys
from datetime import date

TODAY = date.today().isoformat()  # YYYY-MM-DD
BASE_URL = "https://www.palmhillsdevelopments.com/en-us"

# ─── Utility helpers ───────────────────────────────────────────────────────────

def slugify(name: str) -> str:
    """Generate project_id from name."""
    s = name.lower().strip()
    s = s.replace("the ritz-carlton residences cairo, palm hills",
                  "ritz_carlton_residences_cairo_palm_hills")
    s = s.replace("p/x", "p_x")
    s = s.replace("st. 88", "st_88")
    s = s.replace("/", "_")
    s = s.replace(",", "")
    s = s.replace(".", "")
    s = s.replace("-", " ")
    s = s.replace("  ", " ")
    s = "_".join(s.split())
    return s

def jdump(obj):
    """Compact JSON serializer."""
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))

def zone_obj(name, url="", desc="", media=None, brochure=None, src="", dt=TODAY):
    return {
        "zone_name": name,
        "zone_url": url,
        "zone_description": desc,
        "zone_media_urls": media or [],
        "zone_brochure_urls": brochure or [],
        "source_url": src,
        "captured_date": dt,
    }

def listing_obj(project_id, zone_name, unit_type, price_val, currency="EGP",
                bedrooms="unknown", bathrooms="unknown", bua="unknown",
                land="unknown", finishing="unknown", delivery="unknown",
                view="unknown", floor="unknown", furnishing="unknown",
                payment="unknown", dp="unknown", monthly="unknown",
                years="unknown", price_status="official",
                source_type="official_site", source_url="", dt=TODAY):
    return {
        "listing_id": f"{project_id}_{zone_name}_{unit_type}".replace(" ", "_").lower(),
        "project_id": project_id,
        "phase_id": "unknown",
        "zone_name": zone_name,
        "unit_type": unit_type,
        "bedrooms": bedrooms,
        "bathrooms": bathrooms,
        "bua_sqm": bua,
        "land_sqm": land,
        "price_value": price_val,
        "currency": currency,
        "price_per_sqm": "unknown",
        "finishing": finishing,
        "delivery_year": delivery,
        "view": view,
        "floor_number": floor,
        "furnishing_status": furnishing,
        "payment_plan_text": payment,
        "downpayment_value": dp,
        "monthly_value": monthly,
        "years_value": years,
        "price_status": price_status,
        "source_type": source_type,
        "source_url": source_url,
        "captured_date": dt,
    }

def unit_tpl(unit_type, bedrooms="unknown", bua_min="unknown", bua_max="unknown",
             land_min="unknown", land_max="unknown", finishing="unknown",
             price_min="unknown", price_max="unknown", currency="EGP"):
    return {
        "unit_type": unit_type,
        "bedrooms": bedrooms,
        "bua_range_min_sqm": bua_min,
        "bua_range_max_sqm": bua_max,
        "land_range_min_sqm": land_min,
        "land_range_max_sqm": land_max,
        "finishing": finishing,
        "price_range_min": price_min,
        "price_range_max": price_max,
        "currency": currency,
    }

# ─── Region mapping from official listing ──────────────────────────────────────

REGION_MAP = {
    "97_hills": "East",
    "badya": "West",
    "bamboo": "West",
    "bamboo_iii": "West",
    "bamboo_extension": "West",
    "casa": "West",
    "golf_extension": "West",
    "golf_views": "West",
    "hacienda_bay": "Coast",
    "hacienda_blue": "Coast",
    "hacienda_heneish": "Coast",
    "hacienda_waters": "Coast",
    "hacienda_waters_2": "Coast",
    "hacienda_west": "Coast",
    "hacienda_white": "Coast",
    "jirian_palm_hills": "West",
    "new_capital_gardens": "New_Capital",
    "p_x": "West",
    "palm_hills_alexandria": "Alex",
    "palm_hills_katameya_1": "East",
    "palm_hills_katameya_2": "East",
    "palm_hills_new_alamein": "Coast",
    "palm_hills_new_cairo": "East",
    "palm_hills_october": "West",
    "palm_parks": "West",
    "palm_valley": "West",
    "the_crown": "West",
    "the_crown_extension": "West",
    "ritz_carlton_residences_cairo_palm_hills": "West",
    "the_village": "East",
    "village_de_la_capitale": "New_Capital",
    "village_avenue": "East",
    "village_gardens_katameya": "East",
    "village_gate": "East",
    "woodville": "West",
    # Commercial
    "crown_central": "West",
    "palmet_october": "West",
    "palmet_new_cairo": "East",
    "village_gate_mall": "East",
    "golf_central": "West",
    "hale_town": "West",
    "lakeyard": "Coast",
    "palm_central": "West",
    "the_lane": "West",
    "st_88": "unknown",
}

CITY_AREA_MAP = {
    "East": "New Cairo",
    "West": "6th of October / West Cairo",
    "Coast": "North Coast",
    "Alex": "Alexandria",
    "New_Capital": "New Administrative Capital",
    "Sokhna": "Ain Sokhna",
    "unknown": "unknown",
}

# ─── Project data registry ─────────────────────────────────────────────────────

PROJECTS = []

def add_project(name, ptype, segment, brand, status, sales_status, dev_inv,
                url_path, has_detail, has_brochure, zones_raw, description="",
                landmarks=None, amenities=None, unit_types_offered=None,
                tagline="unknown"):
    """Build one project dict with all CSV columns."""
    pid = slugify(name)
    region = REGION_MAP.get(pid, "unknown")
    city_area = CITY_AREA_MAP.get(region, "unknown")

    # Build URL
    if url_path:
        detail_url = f"{BASE_URL}/{url_path}"
    else:
        detail_url = "unknown"

    # Build zones_json
    zones_json = []
    listings_json = []
    unit_templates = []
    unit_types = unit_types_offered or []

    for z in zones_raw:
        zname = z.get("name", "unknown")
        zprice = z.get("price", "unknown")
        zunit = z.get("unit_type", zname)
        zsrc = detail_url if detail_url != "unknown" else ""

        zones_json.append(zone_obj(zname, src=zsrc))

        price_status = "official" if zprice not in ("unknown", "on_request") else zprice
        if zprice not in ("unknown", "on_request"):
            listings_json.append(listing_obj(
                pid, zname, zunit, zprice,
                price_status="official",
                source_url=zsrc
            ))
            unit_templates.append(unit_tpl(zunit, price_min=zprice, price_max=zprice))
        elif zprice == "on_request":
            listings_json.append(listing_obj(
                pid, zname, zunit, "on_request",
                price_status="on_request",
                source_url=zsrc
            ))
            unit_templates.append(unit_tpl(zunit))

        if zunit not in unit_types:
            unit_types.append(zunit)

    # Confidence score
    conf = 0.30  # present in canonical list
    if has_detail:
        conf += 0.20
    if len(zones_json) > 0:
        conf += 0.20
    if has_brochure:
        conf += 0.10
    has_numeric_specs = any(z.get("price", "unknown") not in ("unknown", "on_request") for z in zones_raw)
    if has_numeric_specs:
        conf += 0.10
        conf += 0.10  # also counts as official price
    conf = min(conf, 1.00)

    # Source links
    source_links = []
    if detail_url != "unknown":
        source_links.append(detail_url)
    source_types = ["official_site"] if detail_url != "unknown" else []

    # Disclaimers
    disclaimers = []
    if not has_detail:
        disclaimers.append("Project detail page not found on official site; data limited to listing-level metadata.")
    if any(z.get("price") == "on_request" for z in zones_raw):
        disclaimers.append("Pricing is on request; contact Palm Hills for current quotes.")

    # Sales CTA
    cta = ["Request Sales Call"]
    if has_brochure:
        cta.append("Download Brochures")

    # Landmark proximity
    lm_json = landmarks or []

    # Amenities processing
    am = amenities or {}
    golf_flag = am.get("golf", "unknown")
    beach_flag = am.get("beach", "unknown")
    lagoons_flag = am.get("lagoons", "unknown")
    clubhouse_flag = am.get("clubhouse", "unknown")
    gym_flag = am.get("gym", "unknown")
    pools_flag = am.get("pools", "unknown")
    kids_flag = am.get("kids", "unknown")
    trails_flag = am.get("trails", "unknown")
    retail_flag = am.get("retail", "unknown")
    dining_flag = am.get("dining", "unknown")
    healthcare_flag = am.get("healthcare", "unknown")
    schools_flag = am.get("schools", "unknown")
    mosque_flag = am.get("mosque", "unknown")
    sports_json = am.get("sports", [])
    smart_json = am.get("smart", [])
    sustainability_json = am.get("sustainability", [])

    contact_url = f"{BASE_URL}/contactus"
    inquiry_url = detail_url if detail_url != "unknown" else "unknown"

    row = {
        # Identity
        "project_id": pid,
        "project_name": name,
        "project_aliases_json": jdump([]),
        "brand_family": brand,
        "project_type": ptype,
        "segment": segment,
        "launch_year": "unknown",
        "project_status": status,
        "current_sales_status": sales_status,
        "developer_inventory_status": dev_inv,
        "resale_market_status": "unknown",

        # Geography
        "country": "Egypt",
        "region": region,
        "city_area": city_area,
        "micro_location": "unknown",
        "address_text": "unknown",
        "landmark_proximity_json": jdump(lm_json),
        "roads_access_json": jdump([]),
        "latitude": "unknown",
        "longitude": "unknown",
        "map_link": "unknown",
        "distance_to_airport_km": "unknown",
        "distance_to_cbd_km": "unknown",
        "commute_notes": "unknown",

        # Scale / Masterplan
        "land_area_total_sqm": "unknown",
        "built_up_ratio": "unknown",
        "open_space_ratio": "unknown",
        "unit_count_total": "unknown",
        "buildings_count": "unknown",
        "towers_count": "unknown",
        "phase_count": str(len(zones_json)) if zones_json else "unknown",
        "density_class": "unknown",
        "masterplan_pdf_url": "unknown",
        "masterplan_image_urls_json": jdump([]),

        # Positioning
        "tagline": tagline,
        "positioning_statement": description if description else "unknown",
        "usp_bullets_json": jdump([]),
        "lifestyle_tags_json": jdump([]),
        "target_personas_json": jdump([]),
        "competitive_neighbors_json": jdump([]),
        "investment_angle_notes": "unknown",

        # Inventory
        "unit_types_offered_json": jdump(unit_types),
        "bedrooms_range_min": "unknown",
        "bedrooms_range_max": "unknown",
        "bua_range_min_sqm": "unknown",
        "bua_range_max_sqm": "unknown",
        "land_range_min_sqm": "unknown",
        "land_range_max_sqm": "unknown",
        "finishing_levels_offered_json": jdump([]),
        "view_types_json": jdump([]),
        "parking_type": "unknown",
        "accessibility_features_json": jdump([]),

        # Amenities
        "gated_security_flag": "unknown",
        "security_features_json": jdump([]),
        "clubhouse_flag": clubhouse_flag,
        "gym_flag": gym_flag,
        "pools_flag": pools_flag,
        "pools_details": "unknown",
        "sports_facilities_json": jdump(sports_json),
        "golf_flag": golf_flag,
        "golf_details": "unknown",
        "beach_access_flag": beach_flag,
        "lagoons_flag": lagoons_flag,
        "water_features_notes": "unknown",
        "kids_areas_flag": kids_flag,
        "nurseries_flag": "unknown",
        "trails_flag": trails_flag,
        "retail_on_site_flag": retail_flag,
        "dining_on_site_flag": dining_flag,
        "healthcare_on_site_flag": healthcare_flag,
        "schools_on_site_flag": schools_flag,
        "hospitality_flag": "unknown",
        "coworking_flag": "unknown",
        "mosque_flag": mosque_flag,
        "sustainability_features_json": jdump(sustainability_json),
        "smart_city_features_json": jdump(smart_json),

        # Policies
        "pet_policy_status": "unknown",
        "pet_policy_notes": "unknown",
        "corporate_leasing_status": "unknown",
        "corporate_leasing_notes": "unknown",
        "short_term_rental_status": "unknown",
        "short_term_rental_notes": "unknown",
        "guest_policy_notes": "unknown",
        "parking_policy_notes": "unknown",
        "noise_policy_notes": "unknown",
        "community_rules_doc_url": "unknown",

        # Delivery
        "delivery_schedule_overview": "unknown",
        "delivery_schedule_by_phase_json": jdump({}),
        "handover_process_notes": "unknown",
        "snagging_process_notes": "unknown",
        "warranty_notes": "unknown",
        "maintenance_model": "unknown",
        "service_fee_notes": "unknown",
        "customer_support_channels_json": jdump(["19743"]),

        # Sales / Contact
        "sales_cta_types_json": jdump(cta),
        "brochure_urls_json": jdump([]),
        "gallery_urls_json": jdump([]),
        "sales_office_locations_json": jdump([]),
        "working_hours": "unknown",
        "official_contact_page_url": contact_url,
        "inquiry_form_url": inquiry_url,
        "whatsapp_entry_url": "unknown",
        "email_contact": "unknown",
        "call_center_notes": "Hotline: 19743",

        # Governance
        "source_links_json": jdump(source_links),
        "source_types_json": jdump(source_types),
        "last_verified_date": TODAY,
        "confidence_score": f"{conf:.2f}",
        "disclaimers_json": jdump(disclaimers),

        # Nested entities
        "zones_json": jdump(zones_json),
        "phases_json": jdump([]),
        "unit_templates_json": jdump(unit_templates),
        "listings_json": jdump(listings_json),
        "faqs_json": jdump([]),
    }
    PROJECTS.append(row)

# ─── Populate all 45 projects ──────────────────────────────────────────────────

# === RESIDENTIAL ===

# 1. 97 Hills
add_project("97 Hills", "residential", "premium", "Residential",
    "under_construction", "selling", "available",
    "residential-properties/97-hills", True, True,
    [
        {"name": "Townhouse", "unit_type": "Townhouse", "price": "28.5M"},
        {"name": "Villa", "unit_type": "Villa", "price": "34.3M"},
        {"name": "Family Home", "unit_type": "Family Home", "price": "23.4M"},
    ],
    description="Positioned on the Middle Ring Road, connected to New Cairo's main roads.",
    landmarks=[
        {"landmark": "New Capital Airport", "distance_km": "32"},
        {"landmark": "AUC", "distance_km": "16"},
        {"landmark": "New Capital", "distance_km": "17"},
    ],
    amenities={"retail": "true"},
    tagline="The Perfect Location")

# 2. Badya
add_project("Badya", "residential", "premium", "Residential",
    "under_construction", "selling", "available",
    "residential-properties/city/badya", True, True,
    [
        {"name": "Dae", "unit_type": "Villas/Townhouses", "price": "34.4M"},
        {"name": "Rae", "unit_type": "Villas/Townhouses", "price": "14.7M"},
        {"name": "Signature Courtyards", "unit_type": "Apartments", "price": "10.4M"},
        {"name": "Phase 1", "unit_type": "Villas/Apartments", "price": "25.3M"},
        {"name": "Blu Extension", "unit_type": "Apartments", "price": "10M"},
        {"name": "Ella", "unit_type": "Villas/Townhouses", "price": "17.9M"},
        {"name": "The Village", "unit_type": "Apartments", "price": "9M"},
    ],
    description="Spanning 3,000 acres, focal point for future extensions of West Cairo.",
    landmarks=[
        {"landmark": "Sphinx Airport", "distance_min": "35"},
        {"landmark": "Giza Pyramids / Grand Egyptian Museum", "distance_min": "25"},
    ],
    amenities={"clubhouse": "true", "schools": "true", "healthcare": "true", "sports": ["36 Sports Arenas"]},
    unit_types_offered=["Villa", "Townhouse", "Apartment"],
    tagline="A City Within A City")

# 3. Bamboo
add_project("Bamboo", "residential", "mid", "Residential",
    "delivered", "not_selling", "sold_out",
    "residential-properties/bamboo", True, False,
    [],
    description="Part of Phase 7 of Palm Hills October. Overlooking the 26th of July Corridor.",
    landmarks=[{"landmark": "Gezira Sporting Club", "distance_min": "6"}])

# 4. Bamboo III
add_project("Bamboo III", "residential", "unknown", "Residential",
    "unknown", "unknown", "unknown",
    "", False, False,
    [],
    description="unknown")

# 5. Bamboo Extension
add_project("Bamboo Extension", "residential", "mid", "Residential",
    "delivered", "not_selling", "sold_out",
    "residential-properties/bamboo-extension", True, False,
    [],
    description="Ideally located in the center of 6th of October, overlooking the 26th of July corridor.",
    landmarks=[
        {"landmark": "Gezira Club", "distance_min": "6"},
        {"landmark": "Hyper One", "distance_min": "15"},
    ])

# 6. Casa
add_project("Casa", "residential", "mid", "Residential",
    "delivered", "not_selling", "sold_out",
    "residential-properties/casa", True, False,
    [],
    description="Ideally situated in West Cairo, surrounded by dining and entertainment.",
    landmarks=[
        {"landmark": "Hyper One", "distance_min": "22"},
        {"landmark": "Palm Hills Club", "distance_min": "32"},
        {"landmark": "Sphinx Airport", "distance_min": "25"},
    ])

# 7. Golf Extension
add_project("Golf Extension", "residential", "mid", "Residential",
    "delivered", "not_selling", "sold_out",
    "residential-properties/golf-extension", True, False,
    [],
    description="Located in the heart of 6th of October, close to El Alsson school.",
    landmarks=[
        {"landmark": "Gezira Club", "distance_min": "7"},
        {"landmark": "Palm Central", "distance_min": "6"},
    ])

# 8. Golf Views
add_project("Golf Views", "residential", "mid", "Residential",
    "delivered", "not_selling", "sold_out",
    "residential-properties/golf-views", True, False,
    [],
    description="Located in the heart of 6th of October.",
    landmarks=[
        {"landmark": "Gezira Sporting Club", "distance_min": "4"},
        {"landmark": "Palm Central", "distance_min": "4"},
    ])

# 9. Hacienda Bay
add_project("Hacienda Bay", "residential", "luxury", "Residential",
    "delivered", "selling", "available",
    "residential-properties/hacienda-bay", True, True,
    [
        {"name": "Water Villas", "unit_type": "Villa", "price": "31.3M"},
    ],
    amenities={"beach": "true"},
    tagline="unknown")

# 10. Hacienda Blue
add_project("Hacienda Blue", "residential", "luxury", "Residential",
    "under_construction", "selling", "available",
    "residential-properties/hacienda-blue", True, True,
    [
        {"name": "Villas", "unit_type": "Villa", "price": "58M"},
        {"name": "Chalets", "unit_type": "Chalet", "price": "19M"},
        {"name": "Townhouse", "unit_type": "Townhouse", "price": "31M"},
    ],
    amenities={"beach": "true"})

# 11. Hacienda Heneish
add_project("Hacienda Heneish", "residential", "luxury", "Residential",
    "under_construction", "selling", "available",
    "residential-properties/hacienda-heneish", True, True,
    [
        {"name": "Villa", "unit_type": "Villa", "price": "52.4M"},
        {"name": "Condos", "unit_type": "Condo", "price": "16.9M"},
        {"name": "Cabins", "unit_type": "Cabin", "price": "17.8M"},
        {"name": "Pied Dans L'eau", "unit_type": "Pied Dans L'eau", "price": "94.8M"},
        {"name": "Chalets", "unit_type": "Chalet", "price": "19.5M"},
    ],
    amenities={"beach": "true"})

# 12. Hacienda Waters
add_project("Hacienda Waters", "residential", "luxury", "Residential",
    "under_construction", "selling", "available",
    "residential-properties/hacienda-waters", True, False,
    [
        {"name": "Apartments", "unit_type": "Apartment", "price": "11.2M"},
        {"name": "Villas", "unit_type": "Villa", "price": "106.5M"},
    ],
    amenities={"beach": "true"})

# 13. Hacienda Waters 2
add_project("Hacienda Waters 2", "residential", "luxury", "Residential",
    "under_construction", "selling", "unknown",
    "residential-properties/hacienda-waters-2", True, False,
    [],
    amenities={"beach": "true"})

# 14. Hacienda West
add_project("Hacienda West", "residential", "premium", "Residential",
    "under_construction", "selling", "available",
    "residential-properties/hacienda-west", True, True,
    [
        {"name": "Beach House", "unit_type": "Beach House", "price": "41.2M"},
        {"name": "Lime Chalets", "unit_type": "Chalet", "price": "29.6M"},
        {"name": "Aria Cabanna", "unit_type": "Cabanna", "price": "33.3M"},
    ],
    amenities={"beach": "true"})

# 15. Hacienda White
add_project("Hacienda White", "residential", "premium", "Residential",
    "delivered", "not_selling", "sold_out",
    "residential-properties/hacienda-white", True, False,
    [],
    amenities={"beach": "true"})

# 16. Jirian Palm Hills
add_project("Jirian Palm Hills", "residential", "premium", "Residential",
    "under_construction", "selling", "available",
    "residential-properties/jirian-palm-hills", True, False,
    [
        {"name": "Two Story Villas", "unit_type": "Villa", "price": "on_request"},
        {"name": "One Story Villa", "unit_type": "Villa", "price": "on_request"},
        {"name": "Apartments", "unit_type": "Apartment", "price": "on_request"},
    ])

# 17. New Capital Gardens
add_project("New Capital Gardens", "residential", "mid", "Residential",
    "under_construction", "selling", "available",
    "residential-properties/new-capital-gardens", True, True,
    [
        {"name": "Phase 1", "unit_type": "Mixed", "price": "5.5M"},
        {"name": "Phase 2", "unit_type": "Mixed", "price": "5.5M"},
    ])

# 18. P/X
add_project("P/X", "residential", "unknown", "Residential",
    "unknown", "unknown", "unknown",
    "", False, False,
    [],
    description="unknown")

# 19. Palm Hills Alexandria
add_project("Palm Hills Alexandria", "residential", "premium", "Residential",
    "under_construction", "selling", "available",
    "residential-properties/palm-hills-alexandria", True, True,
    [
        {"name": "Palm Villas", "unit_type": "Villa", "price": "28M"},
        {"name": "Tessera", "unit_type": "Mixed", "price": "23.3M"},
    ])

# 20. Palm Hills Katameya 1
add_project("Palm Hills Katameya 1", "residential", "premium", "Residential",
    "delivered", "not_selling", "sold_out",
    "residential-properties/palm-hills-katameya-1", True, False,
    [])

# 21. Palm Hills Katameya 2
add_project("Palm Hills Katameya 2", "residential", "premium", "Residential",
    "delivered", "not_selling", "sold_out",
    "residential-properties/palm-hills-katameya-2", True, False,
    [])

# 22. Palm Hills New Alamein
add_project("Palm Hills New Alamein", "residential", "luxury", "Residential",
    "under_construction", "selling", "available",
    "residential-properties/palm-hills-new-alamein", True, True,
    [
        {"name": "Alamein Apartments", "unit_type": "Apartment", "price": "8.1M"},
    ],
    amenities={"beach": "true"})

# 23. Palm Hills New Cairo
add_project("Palm Hills New Cairo", "residential", "premium", "Residential",
    "under_construction", "selling", "available",
    "residential-properties/palm-hills-new-cairo", True, True,
    [
        {"name": "Phase 1", "unit_type": "Mixed", "price": "90M"},
        {"name": "Phase 2", "unit_type": "Mixed", "price": "30.7M"},
        {"name": "Phase 3", "unit_type": "Mixed", "price": "20.2M"},
        {"name": "Phase 4", "unit_type": "Mixed", "price": "26.9M"},
        {"name": "Phase 5", "unit_type": "Mixed", "price": "8.9M"},
    ])

# 24. Palm Hills October
add_project("Palm Hills October", "residential", "mid", "Residential",
    "delivered", "not_selling", "sold_out",
    "residential-properties/palm-hills-october", True, False,
    [],
    description="Located in the heart of 6th of October, West Cairo.")

# 25. Palm Parks
add_project("Palm Parks", "residential", "mid", "Residential",
    "delivered", "not_selling", "sold_out",
    "residential-properties/palm-parks", True, True,
    [])

# 26. Palm Valley
add_project("Palm Valley", "residential", "mid", "Residential",
    "delivered", "not_selling", "sold_out",
    "residential-properties/palm-valley", True, False,
    [])

# 27. The Crown
add_project("The Crown", "residential", "luxury", "Residential",
    "under_construction", "selling", "available",
    "residential-properties/the-crown", True, True,
    [
        {"name": "Phase 3", "unit_type": "Mixed", "price": "50.1M"},
    ])

# 28. The Crown Extension
add_project("The Crown Extension", "residential", "luxury", "Residential",
    "under_construction", "selling", "available",
    "residential-properties/the-crown-extension", True, True,
    [
        {"name": "Family Homes", "unit_type": "Family Home", "price": "28M"},
        {"name": "Twin Homes", "unit_type": "Twin Home", "price": "34.9M"},
    ])

# 29. The Ritz-Carlton Residences Cairo, Palm Hills
add_project("The Ritz-Carlton Residences Cairo, Palm Hills", "branded", "luxury", "Residential",
    "unknown", "unknown", "unknown",
    "", False, False,
    [],
    description="unknown")

# 30. The Village
add_project("The Village", "residential", "mid", "Residential",
    "delivered", "not_selling", "sold_out",
    "residential-properties/the-village", True, False,
    [])

# 31. Village de la Capitale
add_project("Village de la Capitale", "residential", "unknown", "Residential",
    "unknown", "unknown", "unknown",
    "", False, False,
    [],
    description="unknown")

# 32. Village Avenue
add_project("Village Avenue", "residential", "mid", "Residential",
    "delivered", "not_selling", "sold_out",
    "residential-properties/village-avenue", True, False,
    [])

# 33. Village Gardens Katameya
add_project("Village Gardens Katameya", "residential", "mid", "Residential",
    "delivered", "not_selling", "sold_out",
    "residential-properties/village-gardens-katameya", True, False,
    [])

# 34. Village Gate
add_project("Village Gate", "residential", "mid", "Residential",
    "delivered", "not_selling", "sold_out",
    "residential-properties/village-gate", True, False,
    [])

# 35. WoodVille
add_project("WoodVille", "residential", "mid", "Residential",
    "delivered", "not_selling", "sold_out",
    "residential-properties/woodville", True, False,
    [])

# === COMMERCIAL (10) ===

# 36. Crown Central
add_project("Crown Central", "commercial", "premium", "Commercial",
    "under_construction", "selling", "available",
    "commercial-properties/crown-central", True, True,
    [
        {"name": "Office Spaces", "unit_type": "Office", "price": "on_request"},
        {"name": "Retail", "unit_type": "Retail", "price": "on_request"},
        {"name": "F&B", "unit_type": "F&B", "price": "on_request"},
    ])

# 37. Palmet October
add_project("Palmet October", "commercial", "premium", "Commercial",
    "under_construction", "selling", "available",
    "commercial-properties/palmet-october", True, True,
    [
        {"name": "F&B", "unit_type": "F&B", "price": "on_request"},
        {"name": "Retail", "unit_type": "Retail", "price": "on_request"},
        {"name": "Office spaces", "unit_type": "Office", "price": "on_request"},
    ])

# 38. Palmet New Cairo
add_project("Palmet New Cairo", "commercial", "premium", "Commercial",
    "under_construction", "selling", "available",
    "commercial-properties/palmet-new-cairo", True, True,
    [
        {"name": "Office spaces", "unit_type": "Office", "price": "on_request"},
    ])

# 39. Village Gate Mall
add_project("Village Gate Mall", "commercial", "premium", "Commercial",
    "under_construction", "selling", "available",
    "commercial-properties/village-gate-mall", True, True,
    [
        {"name": "Offices", "unit_type": "Office", "price": "on_request"},
        {"name": "Clinics", "unit_type": "Clinic", "price": "on_request"},
    ])

# 40. Golf Central
add_project("Golf Central", "commercial", "premium", "Commercial",
    "under_construction", "selling", "available",
    "commercial-properties/golf-central", True, False,
    [])

# 41. Hale Town
add_project("Hale Town", "commercial", "premium", "Commercial",
    "under_construction", "selling", "available",
    "commercial-properties/hale-town", True, False,
    [])

# 42. Lakeyard
add_project("Lakeyard", "commercial", "premium", "Commercial",
    "delivered", "not_selling", "sold_out",
    "commercial-properties/lakeyard", True, False,
    [])

# 43. Palm Central
add_project("Palm Central", "commercial", "mid", "Commercial",
    "delivered", "not_selling", "sold_out",
    "commercial-properties/palm-central", True, False,
    [])

# 44. The Lane
add_project("The Lane", "commercial", "mid", "Commercial",
    "delivered", "not_selling", "sold_out",
    "commercial-properties/the-lane", True, False,
    [])

# 45. St. 88
add_project("St. 88", "commercial", "unknown", "Commercial",
    "unknown", "unknown", "unknown",
    "", False, False,
    [],
    description="unknown")


# ─── CSV writer ────────────────────────────────────────────────────────────────

COLUMNS = [
    # Identity
    "project_id","project_name","project_aliases_json","brand_family","project_type",
    "segment","launch_year","project_status","current_sales_status",
    "developer_inventory_status","resale_market_status",
    # Geography
    "country","region","city_area","micro_location","address_text",
    "landmark_proximity_json","roads_access_json","latitude","longitude","map_link",
    "distance_to_airport_km","distance_to_cbd_km","commute_notes",
    # Scale
    "land_area_total_sqm","built_up_ratio","open_space_ratio","unit_count_total",
    "buildings_count","towers_count","phase_count","density_class",
    "masterplan_pdf_url","masterplan_image_urls_json",
    # Positioning
    "tagline","positioning_statement","usp_bullets_json","lifestyle_tags_json",
    "target_personas_json","competitive_neighbors_json","investment_angle_notes",
    # Inventory
    "unit_types_offered_json","bedrooms_range_min","bedrooms_range_max",
    "bua_range_min_sqm","bua_range_max_sqm","land_range_min_sqm","land_range_max_sqm",
    "finishing_levels_offered_json","view_types_json","parking_type",
    "accessibility_features_json",
    # Amenities
    "gated_security_flag","security_features_json","clubhouse_flag","gym_flag",
    "pools_flag","pools_details","sports_facilities_json","golf_flag","golf_details",
    "beach_access_flag","lagoons_flag","water_features_notes","kids_areas_flag",
    "nurseries_flag","trails_flag","retail_on_site_flag","dining_on_site_flag",
    "healthcare_on_site_flag","schools_on_site_flag","hospitality_flag",
    "coworking_flag","mosque_flag","sustainability_features_json",
    "smart_city_features_json",
    # Policies
    "pet_policy_status","pet_policy_notes","corporate_leasing_status",
    "corporate_leasing_notes","short_term_rental_status","short_term_rental_notes",
    "guest_policy_notes","parking_policy_notes","noise_policy_notes",
    "community_rules_doc_url",
    # Delivery
    "delivery_schedule_overview","delivery_schedule_by_phase_json",
    "handover_process_notes","snagging_process_notes","warranty_notes",
    "maintenance_model","service_fee_notes","customer_support_channels_json",
    # Sales / Contact
    "sales_cta_types_json","brochure_urls_json","gallery_urls_json",
    "sales_office_locations_json","working_hours","official_contact_page_url",
    "inquiry_form_url","whatsapp_entry_url","email_contact","call_center_notes",
    # Governance
    "source_links_json","source_types_json","last_verified_date",
    "confidence_score","disclaimers_json",
    # Nested
    "zones_json","phases_json","unit_templates_json","listings_json","faqs_json",
]

def validate():
    """Run validation checks."""
    errors = []
    # Row count
    if len(PROJECTS) != 45:
        errors.append(f"Expected 45 rows, got {len(PROJECTS)}")

    # Unique IDs
    ids = [p["project_id"] for p in PROJECTS]
    if len(set(ids)) != len(ids):
        dupes = [x for x in ids if ids.count(x) > 1]
        errors.append(f"Duplicate project_ids: {set(dupes)}")

    # JSON parse check
    json_cols = [c for c in COLUMNS if c.endswith("_json")]
    for i, p in enumerate(PROJECTS):
        for jc in json_cols:
            val = p.get(jc, "")
            try:
                json.loads(val)
            except (json.JSONDecodeError, TypeError):
                errors.append(f"Row {i} ({p['project_id']}): {jc} is not valid JSON: {val[:80]}")

    # No empty cells
    for i, p in enumerate(PROJECTS):
        for c in COLUMNS:
            val = p.get(c)
            if val is None or val == "":
                errors.append(f"Row {i} ({p['project_id']}): {c} is empty")

    # Date check
    for i, p in enumerate(PROJECTS):
        d = p.get("last_verified_date", "")
        if len(d) != 10 or d[4] != "-" or d[7] != "-":
            errors.append(f"Row {i}: last_verified_date format invalid: {d}")

    # Confidence range
    for i, p in enumerate(PROJECTS):
        try:
            c = float(p.get("confidence_score", 0))
            if c < 0 or c > 1:
                errors.append(f"Row {i}: confidence_score out of range: {c}")
        except ValueError:
            errors.append(f"Row {i}: confidence_score not numeric")

    return errors


def write_csv(path):
    """Write the master CSV."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(PROJECTS)


def coverage_report():
    """Print coverage statistics."""
    detail_count = sum(1 for p in PROJECTS if p["confidence_score"] != "0.30")
    zone_count = sum(1 for p in PROJECTS if p["zones_json"] != "[]")
    brochure_count = sum(1 for p in PROJECTS if "Download Brochures" in p["sales_cta_types_json"])
    pricing_count = sum(1 for p in PROJECTS if p["listings_json"] != "[]")
    numeric_specs = sum(1 for p in PROJECTS
                       if p["listings_json"] != "[]"
                       and '"price_status":"official"' in p["listings_json"])

    print("=" * 60)
    print("PalmX KB Acquisition — Coverage Report")
    print("=" * 60)
    print(f"Total projects:          {len(PROJECTS)}")
    print(f"Detail pages found:      {detail_count}/45")
    print(f"Projects with zones:     {zone_count}/45")
    print(f"Projects with brochures: {brochure_count}/45")
    print(f"Projects with pricing:   {pricing_count}/45")
    print(f"Numeric specs extracted: {numeric_specs}/45")
    print(f"Last verified date:      {TODAY}")
    print("=" * 60)


if __name__ == "__main__":
    # Validate
    errs = validate()
    if errs:
        print("VALIDATION ERRORS:")
        for e in errs:
            print(f"  ✗ {e}")
        sys.exit(1)
    else:
        print("✓ All validation checks passed")

    # Write CSV
    out_path = "outputs/palmx_projects_master.csv"
    write_csv(out_path)
    print(f"✓ Wrote {out_path} ({len(PROJECTS)} rows, {len(COLUMNS)} columns)")

    # Coverage report
    coverage_report()
