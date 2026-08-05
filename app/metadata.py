"""
Rich schema metadata extraction: primary keys, foreign keys, indexes, row counts,
and sample rows. This is deliberately separate from DatabaseManager.describe_table
(which stays a cheap name/type/nullable lookup) - metadata here is what gets fed
into LLM prompts for better SQL generation, and what the get_database_metadata
MCP tool exposes directly.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import text

if TYPE_CHECKING:
    from .db import DatabaseManager

logger = logging.getLogger(__name__)

SAMPLE_ROW_LIMIT = 5

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _validate_identifier(name: str) -> str:
    """Guard against injection when a table/collection name is interpolated into
    raw SQL/PRAGMA statements (information_schema queries can't parameterize
    identifiers, only values)."""
    if not _IDENTIFIER_RE.match(name):
        raise ValueError(f"Invalid table/collection name: {name!r}")
    return name


@dataclass
class TableMetadata:
    table_name: str
    columns: List[Dict[str, Any]]
    primary_keys: List[str] = field(default_factory=list)
    foreign_keys: List[Dict[str, Any]] = field(default_factory=list)
    indexes: List[Dict[str, Any]] = field(default_factory=list)
    row_count: Optional[int] = None
    sample_rows: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "table_name": self.table_name,
            "columns": self.columns,
            "primary_keys": self.primary_keys,
            "foreign_keys": self.foreign_keys,
            "indexes": self.indexes,
            "row_count": self.row_count,
            "sample_rows": self.sample_rows,
        }


async def _row_count(db_manager: "DatabaseManager", table_name: str) -> Optional[int]:
    try:
        rows = await db_manager.execute_safe_query(f"SELECT COUNT(*) as count FROM {table_name}", limit=1)
        return rows[0]["count"] if rows else None
    except Exception as e:
        logger.warning("Failed to count rows for %s: %s", table_name, e)
        return None


async def _sample_rows(db_manager: "DatabaseManager", table_name: str, limit: int = SAMPLE_ROW_LIMIT) -> List[Dict[str, Any]]:
    try:
        return await db_manager.execute_safe_query(f"SELECT * FROM {table_name}", limit=limit)
    except Exception as e:
        logger.warning("Failed to sample rows for %s: %s", table_name, e)
        return []


async def _fill_postgres_metadata(db_manager: "DatabaseManager", metadata: TableMetadata) -> None:
    table_name = metadata.table_name
    async with db_manager.engine.begin() as conn:
        pk_result = await conn.execute(text("""
            SELECT a.attname
            FROM pg_index i
            JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
            WHERE i.indrelid = :table_name::regclass AND i.indisprimary
        """), {"table_name": table_name})
        metadata.primary_keys = [row[0] for row in pk_result]

        fk_result = await conn.execute(text("""
            SELECT
                kcu.column_name,
                ccu.table_name AS referenced_table,
                ccu.column_name AS referenced_column
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage ccu
                ON tc.constraint_name = ccu.constraint_name AND tc.table_schema = ccu.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_schema = 'public'
              AND tc.table_name = :table_name
        """), {"table_name": table_name})
        metadata.foreign_keys = [
            {"column": row[0], "references_table": row[1], "references_column": row[2]}
            for row in fk_result
        ]

        idx_result = await conn.execute(text("""
            SELECT indexname, indexdef FROM pg_indexes
            WHERE schemaname = 'public' AND tablename = :table_name
        """), {"table_name": table_name})
        metadata.indexes = [{"name": row[0], "definition": row[1]} for row in idx_result]

    metadata.row_count = await _row_count(db_manager, table_name)
    metadata.sample_rows = await _sample_rows(db_manager, table_name)


async def _fill_mysql_metadata(db_manager: "DatabaseManager", metadata: TableMetadata) -> None:
    table_name = metadata.table_name
    async with db_manager.engine.begin() as conn:
        pk_result = await conn.execute(text("""
            SELECT column_name FROM information_schema.key_column_usage
            WHERE table_schema = DATABASE() AND table_name = :table_name
              AND constraint_name = 'PRIMARY'
            ORDER BY ordinal_position
        """), {"table_name": table_name})
        metadata.primary_keys = [row[0] for row in pk_result]

        fk_result = await conn.execute(text("""
            SELECT column_name, referenced_table_name, referenced_column_name
            FROM information_schema.key_column_usage
            WHERE table_schema = DATABASE() AND table_name = :table_name
              AND referenced_table_name IS NOT NULL
        """), {"table_name": table_name})
        metadata.foreign_keys = [
            {"column": row[0], "references_table": row[1], "references_column": row[2]}
            for row in fk_result
        ]

        idx_result = await conn.execute(text(f"SHOW INDEX FROM `{_validate_identifier(table_name)}`"))
        seen = set()
        indexes = []
        for row in idx_result:
            # SHOW INDEX columns: Table, Non_unique, Key_name, Seq_in_index, Column_name, ...
            key_name = row[2]
            if key_name in seen:
                continue
            seen.add(key_name)
            indexes.append({"name": key_name, "unique": row[1] == 0})
        metadata.indexes = indexes

    metadata.row_count = await _row_count(db_manager, table_name)
    metadata.sample_rows = await _sample_rows(db_manager, table_name)


async def _fill_sqlite_metadata(db_manager: "DatabaseManager", metadata: TableMetadata) -> None:
    table_name = _validate_identifier(metadata.table_name)
    async with db_manager.engine.begin() as conn:
        fk_result = await conn.execute(text(f"PRAGMA foreign_key_list({table_name})"))
        metadata.foreign_keys = [
            {"column": row[3], "references_table": row[2], "references_column": row[4]}
            for row in fk_result
        ]

        col_result = await conn.execute(text(f"PRAGMA table_info({table_name})"))
        metadata.primary_keys = [row[1] for row in col_result if row[5]]

        idx_result = await conn.execute(text(f"PRAGMA index_list({table_name})"))
        metadata.indexes = [{"name": row[1], "unique": bool(row[2])} for row in idx_result]

    metadata.row_count = await _row_count(db_manager, table_name)
    metadata.sample_rows = await _sample_rows(db_manager, table_name)


async def _fill_mongo_metadata(db_manager: "DatabaseManager", metadata: TableMetadata) -> None:
    collection_name = metadata.table_name
    collection = db_manager.mongo_database[collection_name]

    try:
        indexes = []
        async for idx in collection.list_indexes():
            indexes.append({
                "name": idx.get("name"),
                "key": dict(idx.get("key", {})),
                "unique": bool(idx.get("unique", False)),
            })
        metadata.indexes = indexes
    except Exception as e:
        logger.warning("Failed to list indexes for %s: %s", collection_name, e)

    metadata.primary_keys = ["_id"]

    # Best-effort FK inference by naming convention (e.g. "customer_id" -> "customers").
    try:
        collection_names = set(await db_manager.mongo_database.list_collection_names())
    except Exception:
        collection_names = set()

    inferred_fks = []
    for col in metadata.columns:
        name = col["column_name"]
        if name.endswith("_id") and name != "_id":
            base = name[:-3]
            for guess in (base, f"{base}s"):
                if guess in collection_names:
                    inferred_fks.append({
                        "column": name,
                        "references_table": guess,
                        "references_column": "_id",
                        "inferred": True,
                    })
                    break
    metadata.foreign_keys = inferred_fks

    metadata.row_count = await _row_count(db_manager, collection_name)
    metadata.sample_rows = await _sample_rows(db_manager, collection_name)


_DIALECT_FILLERS = {
    "postgresql": _fill_postgres_metadata,
    "mysql": _fill_mysql_metadata,
    "sqlite": _fill_sqlite_metadata,
    "mongodb": _fill_mongo_metadata,
}


async def get_table_metadata(db_manager: "DatabaseManager", table_name: str) -> TableMetadata:
    """Build rich metadata for a single table/collection."""
    _validate_identifier(table_name)
    columns = await db_manager.describe_table(table_name)
    metadata = TableMetadata(table_name=table_name, columns=columns)

    filler = _DIALECT_FILLERS.get(db_manager.database_type)
    if filler:
        await filler(db_manager, metadata)

    return metadata


async def get_database_metadata(db_manager: "DatabaseManager", table_name: Optional[str] = None) -> Dict[str, Any]:
    """Metadata for one table, or every table if table_name is None."""
    if table_name:
        return (await get_table_metadata(db_manager, table_name)).to_dict()

    tables = await db_manager.list_tables()
    return {
        "database_type": db_manager.database_type,
        "tables": [
            (await get_table_metadata(db_manager, t["table_name"])).to_dict()
            for t in tables
        ],
    }


def format_metadata_for_prompt(database_metadata: Dict[str, Any]) -> str:
    """Render get_database_metadata()'s output as compact text for an LLM prompt."""
    lines = []
    for table in database_metadata.get("tables", [database_metadata]):
        col_strs = []
        pk_set = set(table.get("primary_keys", []))
        for col in table["columns"]:
            marker = " PK" if col["column_name"] in pk_set else ""
            nullability = "" if col.get("is_nullable", True) else " NOT NULL"
            col_strs.append(f"{col['column_name']} {col['data_type']}{nullability}{marker}")

        fk_strs = [
            f"{fk['column']} -> {fk['references_table']}.{fk['references_column']}"
            for fk in table.get("foreign_keys", [])
        ]

        line = f"Table {table['table_name']} ({table.get('row_count', '?')} rows): " + ", ".join(col_strs)
        if fk_strs:
            line += " | Foreign keys: " + ", ".join(fk_strs)
        if table.get("sample_rows"):
            line += f" | Sample: {table['sample_rows'][0]}"
        lines.append(line)

    return "\n".join(lines)
