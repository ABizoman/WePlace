from openai import OpenAI
import os
import dotenv

dotenv.load_dotenv("../../.env")

client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key=os.getenv("OPENROUTER_API_KEY"),
)

model = "perplexity/sonar"

