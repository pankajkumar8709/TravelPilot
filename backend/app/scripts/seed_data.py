"""Phase 3 demo reference dataset — Delhi (Indian context).

Real coordinates, realistic categories/hours/costs in INR. Cached reference data
the app reads at runtime; stands in for the Overpass/ORS ingestion output.
Travel times + geometry are computed once at seed time (haversine + walking speed).
"""
from __future__ import annotations

# (name, lat, lon, category, interest_tag, opening_hours, avg_visit_min, cost_inr, website)
DELHI_PLACES = [
    ("Red Fort (Lal Qila)", 28.6562, 77.2410, "history", "history", "09:30-16:30", 120, 35.0, "https://www.delhitourism.gov.in"),
    ("Qutub Minar", 28.5245, 77.1855, "history", "history", "07:00-17:00", 90, 40.0, ""),
    ("Humayun's Tomb", 28.5933, 77.2507, "history", "history", "06:00-18:00", 90, 40.0, ""),
    ("India Gate", 28.6129, 77.2295, "outdoor", "outdoor", "00:00-24:00", 45, 0.0, ""),
    ("Lotus Temple", 28.5535, 77.2588, "culture", "culture", "09:00-17:30", 60, 0.0, ""),
    ("Akshardham Temple", 28.6127, 77.2773, "culture", "culture", "09:30-18:30", 150, 0.0, ""),
    ("Jama Masjid", 28.6507, 77.2334, "history", "history", "07:00-12:00,13:30-18:30", 60, 0.0, ""),
    ("National Museum", 28.6117, 77.2190, "culture", "culture", "10:00-18:00", 90, 20.0, ""),
    ("Lodhi Gardens", 28.5931, 77.2197, "outdoor", "outdoor", "06:00-19:30", 60, 0.0, ""),
    ("Chandni Chowk Bazaar", 28.6506, 77.2303, "shopping", "shopping", "10:00-20:00", 90, 0.0, ""),
    ("Dilli Haat", 28.5716, 77.2076, "shopping", "shopping", "10:30-22:00", 75, 30.0, ""),
    ("Raj Ghat", 28.6417, 77.2493, "history", "history", "06:30-18:00", 45, 0.0, ""),
    # food places (used for Phase 4 suggestions, not scheduled)
    ("Karim's (Jama Masjid)", 28.6497, 77.2338, "food", "food", "12:00-23:45", 60, 400.0, ""),
    ("Paranthe Wali Gali", 28.6560, 77.2300, "food", "food", "09:00-22:00", 45, 150.0, ""),
    ("Bukhara (ITC Maurya)", 28.5980, 77.1730, "food", "food", "12:30-14:45,19:00-23:45", 90, 3500.0, ""),
    ("Saravana Bhavan CP", 28.6330, 77.2190, "food", "food", "08:00-23:00", 45, 300.0, ""),
    ("Andhra Bhavan Canteen", 28.6135, 77.2280, "food", "food", "08:00-22:30", 45, 250.0, ""),
    # hotels (used for Phase 4 stay suggestions)
    ("The Imperial New Delhi", 28.6280, 77.2185, "hotel", "hotel", "24/7", 0, 12000.0, ""),
    ("Bloomrooms @ Janpath", 28.6260, 77.2190, "hotel", "hotel", "24/7", 0, 3500.0, ""),
    ("Haveli Dharampura", 28.6520, 77.2360, "hotel", "hotel", "24/7", 0, 8000.0, ""),
]

# (name, lat, lon, type)
DELHI_AMENITIES = [
    ("Public Toilet Connaught Place", 28.6330, 77.2190, "toilets"),
    ("Toilet Red Fort", 28.6560, 77.2405, "toilets"),
    ("SBI ATM CP", 28.6320, 77.2200, "atm"),
    ("HDFC ATM Karol Bagh", 28.6510, 77.1900, "atm"),
    ("Apollo Pharmacy CP", 28.6315, 77.2185, "pharmacy"),
    ("MedPlus Chandni Chowk", 28.6500, 77.2310, "pharmacy"),
]

# Back-compat aliases so existing imports (PARIS_*) keep working.
PARIS_PLACES = DELHI_PLACES
PARIS_AMENITIES = DELHI_AMENITIES
