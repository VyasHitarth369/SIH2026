import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
# Per CONCORDIA_BACKEND_CONTEXT.md, the server-side secret key is SUPABASE_SECRET_KEY.
# Supports fallback to SUPABASE_KEY for backwards compatibility.
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_KEY")

if not SUPABASE_URL:
    raise ValueError(
        "Missing SUPABASE_URL in environment. Please define SUPABASE_URL in Backend/.env"
    )

if not SUPABASE_SECRET_KEY:
    raise ValueError(
        "Missing SUPABASE_SECRET_KEY in environment. Please define SUPABASE_SECRET_KEY in Backend/.env"
    )

# Singleton Supabase client instance — credentials are never exposed
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)


def get_supabase() -> Client:
    """Dependency and accessor for the singleton Supabase client.

    Route handlers and services must use this rather than re-creating
    client instances across files.
    """
    return supabase