from __future__ import annotations

from typing import Dict, List
from uuid import uuid4

from app.infrastructure.db import db_cursor


class ProjectService:
    def create_project(self, name: str) -> Dict[str, str]:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Project name must not be empty.")
        collection_id = clean_name.lower().replace(" ", "-")
        project_id = str(uuid4())
        with db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO projects (id, name, collection_id)
                VALUES (?, ?, ?)
                """,
                (project_id, clean_name, collection_id),
            )
        return {"id": project_id, "name": clean_name, "collection_id": collection_id}

    def list_projects(self) -> List[Dict[str, str]]:
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT id, name, collection_id, created_at
                FROM projects
                WHERE archived_at IS NULL
                ORDER BY created_at ASC
                """
            )
            rows = cur.fetchall()
        projects = [dict(r) for r in rows]
        if projects:
            return projects
        # Ensure a default project exists for backward compatibility.
        return [self.ensure_default_project()]

    def ensure_default_project(self) -> Dict[str, str]:
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT id, name, collection_id, created_at
                FROM projects
                WHERE collection_id = 'default'
                LIMIT 1
                """
            )
            row = cur.fetchone()
            if row:
                return dict(row)
            project_id = str(uuid4())
            cur.execute(
                """
                INSERT INTO projects (id, name, collection_id)
                VALUES (?, 'Default', 'default')
                """,
                (project_id,),
            )
            return {
                "id": project_id,
                "name": "Default",
                "collection_id": "default",
            }

    def get_project(self, project_id: str) -> Dict[str, str]:
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT id, name, collection_id, created_at
                FROM projects
                WHERE id = ? AND archived_at IS NULL
                LIMIT 1
                """,
                (project_id,),
            )
            row = cur.fetchone()
        if not row:
            raise ValueError(f"Unknown project_id: {project_id}")
        return dict(row)
