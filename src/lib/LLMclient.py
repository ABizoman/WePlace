from openai import OpenAI
import os
import dotenv
import json

# Load environment variables
dotenv.load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'), override=True)

# Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = "https://openrouter.ai/api/v1"
MODEL = "perplexity/sonar" # Using Perplexity Sonar model

# Initialize Client
client = OpenAI(
  base_url=BASE_URL,
  api_key=OPENROUTER_API_KEY,
)

def validate_update_with_llm(current_data: dict, update_data: dict) -> dict:
    """
    Validates a place update using the Perplexity LLM.
    
    Args:
        current_data (dict): The existing data for the place.
        update_data (dict): The proposed changes.
        
    Returns:
        dict: A dictionary containing 'valid' (bool) and 'reason' (str).
    """
    
    system_prompt = """
    You are an intelligent data validation assistant for a map/places database.
    Your task is to verify if a proposed update to a place is legitimate, accurate, and safe.
    You should check for:
    1. Vandalism (e.g. offensive names, fake data).
    2. Consistency (e.g. does the category match the name?).
    3. Plausibility (e.g. does the info generally make sense?).

    please look at websites like google maps, yelp, instagram... to verify the data and the updates aren't just made up.

    pay attention to even small changes likes typos or name, these should be rejected unless they reflect the actual name of businessa according to most other sources.

    You are given the old data and the new data so you can compare them and see what changed and if this changes makes sense.
    
    You must output your decision in STRICT JSON format.
    The JSON object must have exactly these keys:
    - "valid": boolean (true if accepted, false if rejected)
    - "reason": string (a concise explanation of your decision)
    """
    
    user_prompt = f"""
    Please validate the following update:
    
    --- CURRENT DATA ---
    {json.dumps(current_data, indent=2)}
    
    --- PROPOSED UPDATE ---
    {json.dumps(update_data, indent=2)}
    
    Respond with the JSON object.
    """
    
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            # Perplexity/Sonar on OpenRouter may not support response_format={"type": "json_object"}
            # rely on prompt engineering and manual parsing instead
        )
        
        content = response.choices[0].message.content.strip()
        
        # Robust JSON extraction
        try:
            # Find the first '{' and last '}'
            start_idx = content.find('{')
            end_idx = content.rfind('}')
            
            if start_idx != -1 and end_idx != -1:
                json_str = content[start_idx:end_idx+1]
                result = json.loads(json_str)
            else:
                # Fallback: try to load the whole content if no braces found (unlikely for JSON)
                result = json.loads(content)
        except json.JSONDecodeError:
             print(f"Failed to parse JSON. Raw content: {content}")
             return {
                 "valid": False,
                 "reason": f"LLM returned invalid format. Raw response: {content[:100]}..."
             }
        
        # Ensure keys exist
        if "valid" not in result:
            result["valid"] = False
            result["reason"] = "LLM response missing 'valid' key."
            
        return result
        
    except Exception as e:
        print(f"Error during LLM validation: {e}")
        # Default to False for safety in case of error, or True if you want to be lenient.
        # Given this is an automated system, rejecting on error is safer, or we can flag for manual review.
        return {
            "valid": False, 
            "reason": f"Validation process failed: {str(e)}"
        }


