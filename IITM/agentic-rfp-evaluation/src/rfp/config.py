import os
from dotenv import load_dotenv

# Load local environment variables from .env.
load_dotenv()


def get_local_api_key() -> str:
    """Read the OpenAI API key from the local environment."""
    return os.getenv("OPENAI_API_KEY", "").strip()