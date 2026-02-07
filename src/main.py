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
def search_places(q: str = Query(..., min_length=3)):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Simple SQL LIKE search on name and description
    query = """
        SELECT * FROM places 
        WHERE name LIKE ? OR description LIKE ? OR subcategory LIKE ?
        LIMIT 20
    """
    search_term = f"%{q}%"
    
    # Search name, description, OR even the type (e.g. search for 'pizza')
    cursor.execute(query, (search_term, search_term, search_term))
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