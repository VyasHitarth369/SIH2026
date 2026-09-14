from typing import Any, Dict, List, Optional
from app.database import get_supabase


class BaseService:
    """Reusable database access service for Supabase tables.

    Provides common CRUD helpers so table operations do not duplicate
    query code across routes.
    """

    def __init__(self, table_name: str):
        self.table_name = table_name

    @property
    def client(self):
        return get_supabase()

    def get_all(
        self,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = "created_at",
        desc: bool = True,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        query = self.client.table(self.table_name).select("*")
        if filters:
            for k, v in filters.items():
                if v is not None:
                    query = query.eq(k, v)
        if order_by:
            query = query.order(order_by, desc=desc)
        query = query.limit(limit)
        response = query.execute()
        return response.data or []

    def get_by_field(self, field: str, value: Any) -> Optional[Dict[str, Any]]:
        response = (
            self.client.table(self.table_name)
            .select("*")
            .eq(field, value)
            .execute()
        )
        return response.data[0] if response.data else None

    def insert(self, data: Dict[str, Any]) -> Dict[str, Any]:
        response = self.client.table(self.table_name).insert(data).execute()
        return response.data[0] if response.data else data

    def update(self, id_field: str, id_value: Any, patch: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        response = (
            self.client.table(self.table_name)
            .update(patch)
            .eq(id_field, id_value)
            .execute()
        )
        return response.data[0] if response.data else None

    def delete(self, id_field: str, id_value: Any):
        return (
            self.client.table(self.table_name)
            .delete()
            .eq(id_field, id_value)
            .execute()
        )
