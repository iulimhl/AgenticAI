import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
assert api_key, "ERROR: GEMINI_API_KEY not found. Check your .env file!"
client = genai.Client(
    http_options=types.HttpOptions(
        retry_options=types.HttpRetryOptions(attempts=6, initial_delay=2.0)
    )
)

response = client.models.generate_content(
    model="gemini-3.5-flash-lite",
    contents="Reply with the exact phrase: 'Telemetry online.'"
)
print(response.text)
