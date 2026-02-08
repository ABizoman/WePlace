from fastapi import FastAPI, HTTPException, Query
import sqlite3
import os
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from utils import calculate_distance_km
import updateService




class PlaceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    opening_hours: Optional[str] = None


class PlaceCreate(BaseModel):
    name: str
    lat: float
    lon: float
    category: str
    subcategory: str
    address: Optional[str] = None
    description: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    opening_hours: Optional[str] = None


from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="WePlace API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Database Path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "oxford.db")

def get_db_connection():
    if not os.path.isfile(DB_PATH):
        if os.path.isfile("oxford.db"):
            conn = sqlite3.connect("oxford.db")
        else:
            raise HTTPException(status_code=500, detail="Database file not found. Run scripts/build_oxford_db.py first.")
    else:
        conn = sqlite3.connect(DB_PATH)
        
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/")
def read_root():
    return {
        "message": "Welcome to Oxford Places API", 
        "endpoints": [
            "/places?limit=10&offset=0", 
            "/places/search?q=coffee&lat=51.75&lon=-1.25", 
            "/categories"
        ]
    }

@app.get("/places")
def get_places(
    category: Optional[str] = None, 
    subcategory: Optional[str] = None,
    limit: int = 50, 
    offset: int = 0
):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM places"
    params = []
    conditions = []
    
    if category:
        conditions.append("category = ?")
        params.append(category)
        
    if subcategory:
        conditions.append("subcategory = ?")
        params.append(subcategory)
        
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
        
    query += " LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

@app.get("/places/search")
def search_places(
    q: str = Query(..., min_length=3), 
    limit: int = 20,
    lat: Optional[float] = None, # User's Latitude
    lon: Optional[float] = None, # User's Longitude
    proximity_weight: float = 0.5 # How much distance impacts score (0.0 to 2.0 recommended)
):
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Try using RapidFuzz for fuzzy/tolerant search
    try:
        from rapidfuzz import fuzz
        
        # 1. Fetch EVERYTHING
        cursor.execute("SELECT * FROM places")
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        scored_results = []
        q_lower = q.lower()
        
        # Basic smart synonyms to bridge gap between "coffee" and "cafe"
        synonyms = {
            "coffee": ["cafe", "coffee_shop"],
            "drink": ["pub", "bar", "nightclub"],
            "food": ["restaurant", "fast_food"],
            "books": ["library", "bookshop"],
            "sleep": ["hotel", "hostel", "guest_house"]
        }
        
        # Check if query contains any synonym keywords
        target_subcats = set()
        for word in q_lower.split():
            if word in synonyms:
                target_subcats.update(synonyms[word])
        
        for row in rows:
            # 1. Name & Description: Use Partial Ratio
            s_name = fuzz.partial_ratio(q_lower, str(row.get('name', '')).lower())
            s_desc = fuzz.partial_ratio(q_lower, str(row.get('description', '')).lower())
            
            # 2. Category & Subcategory: Use STRICT Ratio
            cat_val = str(row.get('category', '')).lower()
            sub_val = str(row.get('subcategory', '')).lower()
            
            s_cat = fuzz.ratio(q_lower, cat_val)
            s_sub = fuzz.ratio(q_lower, sub_val)
            
            # 3. Synonym Boost
            if sub_val in target_subcats:
                s_sub = 100
            
            # Base Relevance Score
            base_score = max(s_name, s_sub, s_cat, s_desc)
            
            # 4. Proximity Boost (if lat/lon provided)
            bonus_score = 0
            dist_km = float('inf')
            
            # Use utility function here
            # Use utility function here
            if lat is not None and lon is not None and row['lat'] and row['lon']:
                dist_km = calculate_distance_km(lat, lon, row['lat'], row['lon'])
                
                # Proximity Score Function: decay
                # 0km -> 100
                # 1km -> ~66
                # 5km -> ~16
                proximity_score = 100 / (1 + 0.5 * dist_km)
                
                # Add to total with weight
                bonus_score = proximity_score * proximity_weight

            final_score = base_score + bonus_score
            
            # Threshold (check base_score to ensure relevance first, then rank by proximity)
            if base_score > 55:
                # Add distance to result for client convenience
                # Convert row to dict to modify it
                item = dict(row) 
                item['distance_km'] = round(dist_km, 2) if (lat is not None and lon is not None and row['lat'] and row['lon']) else None
                item['score'] = round(final_score, 1)
                scored_results.append((final_score, item))

                
        # Sort by score descending
        scored_results.sort(key=lambda x: x[0], reverse=True)
        
        return [item[1] for item in scored_results[:limit]]

    except ImportError:
        # Fallback to SQL LIKE search if library fails
        print("Warning: rapidfuzz not installed, using basic SQL search")
        query = """
            SELECT * FROM places 
            WHERE 
                name LIKE ? OR 
                address LIKE ? OR 
                category LIKE ? OR 
                subcategory LIKE ? OR 
                description LIKE ?
            LIMIT ?
        """
        search_term = f"%{q}%"
        cursor.execute(query, (search_term, search_term, search_term, search_term, search_term, limit))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

@app.post("/places/{place_id}/update")
def update_place(place_id: int, update: PlaceUpdate):
    conn = get_db_connection()
    
    # Convert Pydantic model to dict, excluding None values
    update_data = {k: v for k, v in update.dict().items() if v is not None}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields provided for update")
        
    result = updateService.perform_update(place_id, update_data, conn)
    conn.close()
    
    if result["status"] == "error":
        raise HTTPException(status_code=404, detail=result["message"])
    elif result["status"] == "rejected":
        # We return 200 OK even if rejected, but with the specific status and message
        # Or you could use 400 Bad Request, but 200 with "status": "rejected" is often better for logic flow
        return result
        
    return result

@app.post("/places")
def create_place(place: PlaceCreate):
    conn = get_db_connection()
    
    # Convert Pydantic model to dict
    place_data = place.dict()
    
    result = updateService.perform_creation(place_data, conn)
    conn.close()
    
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    elif result["status"] == "rejected":
        return result
        
    return result

@app.get("/categories")
def get_categories():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT DISTINCT category, subcategory 
        FROM places 
        WHERE category != 'other' 
        ORDER BY category, subcategory
    """)
    rows = cursor.fetchall()
    conn.close()
    
    result: Dict[str, List[str]] = {}
    for row in rows:
        cat = row['category']
        sub = row['subcategory']
        
        if cat not in result:
            result[cat] = []
        result[cat].append(sub)
        
    return result