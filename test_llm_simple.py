import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from lib.LLMclient import validate_update_with_llm
import json

current = {"name": "Test Place", "category": "coffee"}
update = {"name": "Test Place Updated", "category": "coffee_shop"}

print("Testing LLM validation...")
try:
    result = validate_update_with_llm(current, update)
    print("Result:", json.dumps(result, indent=2))
except Exception as e:
    print("Error:", e)
