import math
from datetime import datetime
import random # For simulation

def calculate_staleness(place_id: int, db_connection) -> float:
    """
    Calculates the staleness of a place's data.
    Returns a score from 0.0 (fresh) to 1.0 (very stale).
    """
    cursor = db_connection.cursor()
    cursor.execute("SELECT last_updated FROM places WHERE rowid = ?", (place_id,)) # Assuming rowid for now or osmid if mapped
    row = cursor.fetchone()
    
    if not row or not row['last_updated']:
        return 1.0 # Treat as very stale if no info
        
    last_updated_str = row['last_updated']
    try:
        last_updated = datetime.fromisoformat(last_updated_str)
        now = datetime.now()
        delta = now - last_updated
        days_diff = delta.days
        
        # Staleness Logic:
        # 0 days -> 0.0
        # 30 days -> 0.2
        # 365 days -> 1.0
        staleness = min(days_diff / 365.0, 1.0)
        return staleness
        
    except ValueError:
        return 1.0

def calculate_relevance(place_id: int, db_connection) -> float:
    """
    Calculates the relevance of the business.
    Returns a score from 0.0 (irrelevant) to 1.0 (highly relevant).
    Placeholder: Random score or based on category popularity?
    For now: Random to simulate 'Call Volume' or 'Search Volume'.
    """
    # TODO: Connect to actual analytics (number of API calls for this place)
    # base_relevance = get_analytics_count(place_id) / max_possible_count
    return random.uniform(0.1, 0.9)

def calculate_compensation(staleness: float, relevance: float) -> float:
    """
    Calculates compensation amount based on staleness and relevance.
    Compensation = f(staleness * relevance)
    """
    # Simple formula: Base Rate * Staleness * Relevance
    BASE_RATE = 10.0 # e.g., $10 max or 10 credits
    
    # We want to incentivize updating STALE and POPULAR places.
    factor = staleness * relevance # Both are 0-1
    
    amount = BASE_RATE * factor
    return round(amount, 2)

def validate_update(update_data: dict, current_data: dict) -> dict:
    """
    Validates the update using an LLM (Simulated).
    Returns a dict with 'valid' (bool) and 'reason' (str).
    """
    # TODO: Integrate with Grok/Perplexity/GPT-4 API here.
    # Prompt: "Fact check this update: {update_data} for place: {current_data}"
    
    # Simulation: 
    # If the name is changed to something suspicious, reject.
    # Otherwise accept.
    
    print(f"DEBUG: Simulating LLM Validation for update: {update_data}")
    
    if 'name' in update_data:
        new_name = update_data['name'].lower()
        if "fake" in new_name or "scam" in new_name:
            return {"valid": False, "reason": "LLM Flagged: Potential spam/fake name detected."}
            
    return {"valid": True, "reason": "LLM Verification: Data seems consistent with public records."}

def perform_update(place_id: int, update_data: dict, db_connection) -> dict:
    """
    Orchestrates the update process.
    """
    cursor = db_connection.cursor()
    
    # 1. Fetch current data
    cursor.execute("SELECT * FROM places WHERE rowid = ?", (place_id,))
    row = cursor.fetchone()
    
    if not row:
        return {"status": "error", "message": "Place not found"}
        
    current_data = dict(row)
    
    # 2. Validate Update (LLM)
    validation = validate_update(update_data, current_data)
    if not validation['valid']:
        return {
            "status": "rejected",
            "message": validation['reason'],
            "compensation": 0.0
        }
    
    # 3. Calculate metrics based on OLD state
    staleness = calculate_staleness(place_id, db_connection)
    relevance = calculate_relevance(place_id, db_connection)
    compensation = calculate_compensation(staleness, relevance)
    
    # 4. Apply Update (Placeholder actual SQL update for specific fields)
    # We only update fields provided in update_data
    # And ALWAYS update 'last_updated'
    
    fields = []
    values = []
    
    for key, value in update_data.items():
        # Prevent updating protected fields if any
        if key in ['id', 'rowid', 'osmid', 'lat', 'lon']: 
             continue # Skip structural fields for now for safety
        fields.append(f"{key} = ?")
        values.append(value)
        
    fields.append("last_updated = ?")
    values.append(datetime.now().isoformat())
    
    # WHERE id
    values.append(place_id)
    
    if fields:
        sql = f"UPDATE places SET {', '.join(fields)} WHERE rowid = ?"
        cursor.execute(sql, values)
        db_connection.commit()
    
    return {
        "status": "success",
        "message": "Update accepted",
        "compensation": compensation,
        "details": {
            "staleness_score": round(staleness, 2),
            "relevance_score": round(relevance, 2),
            "validation_note": validation['reason']
        }
    }
