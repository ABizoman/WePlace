from fastapi import FastAPI, HTTPException, Query
import sqlite3
import os
from typing import List, Optional, Dict

app = FastAPI(title="WePlace API")

# Database Path - Assumes oxford.db is at project root
# BASE_DIR should point to parent of src
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "oxford.db")

def get_db_connection():
    if not os.path.isfile(DB_PATH):
        # Fallback for when running locally in strange CWD
        if os.path.isfile("oxford.db"):
            conn = sqlite3.connect("oxford.db")
        else:
            raise HTTPException(status_code=500, detail="Database file not found. Run scripts/build_oxford_db.py first.")
    else:
        conn = sqlite3.connect(DB_PATH)
        
    conn.row_factory = sqlite3.Row  # Access columns by name
    return conn

@app.get("/")
def read_root():
    return {
        "message": "Welcome to Oxford Places API", 
        "endpoints": [
            "/places?limit=10&offset=0", 
            "/places/search?q=coffee", 
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
    
    # Base query
    query = "SELECT * FROM places"
    params = []
    conditions = []
    
    # Dynamic filtering
    if category:
        conditions.append("category = ?")
        params.append(category)
        
    if subcategory:
        conditions.append("subcategory = ?")
        params.append(subcategory)
        
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
        
    # Pagination
    query += " LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    # Convert 'sqlite3.Row' objects to dicts
    return [dict(row) for row in rows]

@app.get("/places/search")
def search_places(q: str = Query(..., min_length=3), limit: int = 20):
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Try using RapidFuzz for fuzzy/tolerant search
    try:
        from rapidfuzz import fuzz, utils
        
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
            # 1. Name & Description: Use Partial Ratio (substring match is fine)
            # "Starbucks" matches "Starbucks Coffee" -> Good.
            s_name = fuzz.partial_ratio(q_lower, str(row.get('name', '')).lower())
            s_desc = fuzz.partial_ratio(q_lower, str(row.get('description', '')).lower())
            
            # 2. Category & Subcategory: Use STRICT Ratio
            # Prevents "coffee shop" from matching "shop" (Lidl) with 100% score
            cat_val = str(row.get('category', '')).lower()
            sub_val = str(row.get('subcategory', '')).lower()
            
            s_cat = fuzz.ratio(q_lower, cat_val)
            s_sub = fuzz.ratio(q_lower, sub_val)
            
            # 3. Synonym Boost
            # If the place's subcategory matches a synonym of the query, give it max score
            if sub_val in target_subcats:
                s_sub = 100
            
            # Weighted Final Score
            # We prioritize Name and Subcategory matches
            final_score = max(s_name, s_sub, s_cat, s_desc)
            
            # Threshold
            if final_score > 60:
                scored_results.append((final_score, row))
                
        # Sort by score descending
        scored_results.sort(key=lambda x: x[0], reverse=True)
        
        # Return top matches
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

@app.get("/categories")
def get_categories():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get distinct (Category, Subcategory) pairs
    cursor.execute("""
        SELECT DISTINCT category, subcategory 
        FROM places 
        WHERE category != 'other' 
        ORDER BY category, subcategory
    """)
    rows = cursor.fetchall()
    conn.close()
    
    # Group them: { "amenity": ["cafe", "pub"], "shop": ["bakery"] }
    result: Dict[str, List[str]] = {}
    for row in rows:
        cat = row['category']
        sub = row['subcategory']
        
        if cat not in result:
            result[cat] = []
        result[cat].append(sub)
        
    return result