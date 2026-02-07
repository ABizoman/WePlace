import osmnx as ox
import pandas as pd
import sqlite3
import json

# config
PLACE_NAME = "Oxford, UK"
DB_NAME = "oxford.db"

# place categories we are fetching by type
# This list covers the user's request for "local business, schools, coffee shops restaurants"
TAGS = {
    "shop": True, 
    "tourism": ["hotel", "hostel", "guest_house", "museum", "gallery", "attraction", "viewpoint"],
    "amenity": [
        "restaurant", "cafe", "pub", "bar", "fast_food", "ice_cream", 
        "pharmacy", "bank", "library", "university", "school", "college", 
        "kindergarten", "parking", "bicycle_parking", "cinema", "theatre", 
        "nightclub", "community_centre", "place_of_worship"
    ]
}

def fetch_oxford_data():
    print(f"Fetching data for {PLACE_NAME} from OpenStreetMap...")
    print("This might take a minute... huge fetch incoming.")
    
    # ox.features_from_place returns a GeoDataFrame with all features matching tags
    gdf = ox.features_from_place(PLACE_NAME, TAGS)
    
    print(f"Raw objects fetched: {len(gdf)}")
    return gdf

def process_data(gdf):
    print("Processing data...")
    
    # 1. Coordinate Handling (No Polygons!)
    # Convert everything to a single point (centroid)
    centroids = gdf.geometry.centroid
    gdf['lat'] = centroids.y
    gdf['lon'] = centroids.x
    
    # Reset index to make osmid accessible as a column
    gdf = gdf.reset_index()

    # 2. Ensure all potential columns exist to avoid KeyErrors
    potential_cols = [
        'addr:housenumber', 'addr:street', 'addr:postcode', 
        'opening_hours', 'website', 'url', 'phone', 'contact:phone', 'contact:website',
        'amenity', 'shop', 'tourism', 'name'
    ]
    for col in potential_cols:
        if col not in gdf.columns:
            gdf[col] = None

    # 3. Categorization Helper
    def get_category_type(row):
        # Determine the primary category and sub-type
        if pd.notna(row.get('amenity')):
            return 'amenity', row['amenity']
        if pd.notna(row.get('shop')):
            return 'shop', row['shop']
        if pd.notna(row.get('tourism')):
            return 'tourism', row['tourism']
        return 'other', 'unknown'

    # 4. Address Helper
    def get_address(row):
        parts = []
        number = row.get('addr:housenumber')
        street = row.get('addr:street')
        postcode = row.get('addr:postcode')
        
        if pd.notna(number): parts.append(str(number))
        if pd.notna(street): parts.append(str(street))
        if pd.notna(postcode): parts.append(str(postcode))
        
        return " ".join(parts) if parts else ""

    # 5. Description Generator (Fallback)
    def get_description(row, category, subcategory, address):
        # If we had a real 'description' column in OSM, we'd use it, but it's rare (<4%)
        # So we synthesize one.
        name = row.get('name', 'This place')
        if pd.isna(name): name = "This place"
        
        desc = f"{name} is a {subcategory}"
        if address:
            desc += f" located at {address}."
        else:
            desc += " in Oxford."
            
        return desc

    # Apply transformations row by row
    # Note: Vectorization is faster but this is cleaner for complex logic and dataset is small (<5k)
    processed_rows = []
    
    for _, row in gdf.iterrows():
        cat, subcat = get_category_type(row)
        address = get_address(row)
        name = row.get('name')
        if pd.isna(name):
            name = "Unknown"
            
        desc = get_description(row, cat, subcat, address)
        
        # Consolidate Phone/Website
        phone = row.get('phone') or row.get('contact:phone')
        website = row.get('website') or row.get('url') or row.get('contact:website')
        
        processed_rows.append({
            'osmid': row.get('id'),
            'name': name,
            'category': cat,
            'subcategory': subcat,
            'address': address,
            'description': desc,
            'opening_hours': row.get('opening_hours'),
            'phone': phone,
            'website': website,
            'lat': row['lat'],
            'lon': row['lon'],
            'last_updated': pd.Timestamp.now().isoformat()
        })
        
    df = pd.DataFrame(processed_rows)
    
    # 6. Metadata (JSON) for everything else
    # We'll skip this for now to keep the DB clean as requested by "Point MVP"
    # usage. If needed, we can add it back.
    
    return df

def save_to_sqlite(df, db_name):
    print(f"Saving {len(df)} records to {db_name}...")
    conn = sqlite3.connect(db_name)
    
    # Write to table 'places'
    df.to_sql('places', conn, if_exists='replace', index=False)
    
    # Create indexes for speed
    cursor = conn.cursor()
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_places_lat_lon ON places(lat, lon)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_places_category ON places(category)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_places_name ON places(name)")
    
    conn.commit()
    conn.close()
    print("Done! Database is ready.")

if __name__ == "__main__":
    # Settings to avoid clutter
    ox.settings.log_console = False
    
    gdf = fetch_oxford_data()
    df = process_data(gdf)
    save_to_sqlite(df, DB_NAME)
