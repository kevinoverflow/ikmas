from openai import OpenAI
from app.infrastructure.config import BASE_URL, API_KEY

def get_client() -> OpenAI:
    if not API_KEY:
        raise RuntimeError("Missing API key (SCADS_API_KEY / OPENAI_API_KEY).")
    return OpenAI(base_url=BASE_URL, api_key=API_KEY)