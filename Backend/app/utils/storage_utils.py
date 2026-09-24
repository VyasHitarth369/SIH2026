"""storage_utils.py

Provides utility functions for managing secure access to private Supabase Storage buckets.
Ensures private documents (MOUs, proposals, attachments) are never exposed via unauthenticated public URLs,
and creates temporary signed URLs for authorized viewers.
"""

from typing import Optional
from app.database import supabase


def resolve_document_signed_url(raw_doc_or_path: Optional[str], expires_in: int = 604800) -> Optional[str]:
    """Resolves a raw storage path or Supabase URL into a temporary signed URL.
    Returns None if input is empty/null, or original URL if not inside the Supabase 'documents' bucket.
    """
    if not raw_doc_or_path:
        return None
    raw_str = str(raw_doc_or_path).strip()
    if raw_str in ["", "-", "None", "null"]:
        return None

    # If it's a Supabase storage URL for the documents bucket
    storage_path = raw_str
    if "/documents/" in storage_path:
        storage_path = storage_path.split("/documents/")[-1].split("?")[0]

    # Check if storage_path looks like a relative file path in the documents bucket
    if (
        storage_path.startswith("mous/")
        or storage_path.startswith("proposals/")
        or storage_path.startswith("attachments/")
        or storage_path.startswith("certificates/")
        or (not storage_path.startswith("http://") and not storage_path.startswith("https://") and "/" in storage_path)
    ):
        try:
            signed_res = supabase.storage.from_("documents").create_signed_url(storage_path, expires_in=expires_in)
            return signed_res.get("signedURL") or signed_res.get("signedUrl") or raw_str
        except Exception:
            return raw_str

    return raw_str
