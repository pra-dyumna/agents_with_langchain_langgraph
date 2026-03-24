import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_GENAI_API_KEY = os.getenv("GOOGLE_GENAI_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
