"""
Natural Language to SQL Converter

Uses a configured LLM provider (Anthropic, OpenAI, OpenRouter, or Ollama - see
app/llm_providers.py) to convert natural language queries to SQL, with a
rule-based fallback when no provider is configured or the LLM call fails.
"""

import logging
import re
from typing import Any, Dict, List, Optional

try:
    from .llm_providers import LLMProvider, get_llm_provider
except ImportError:
    # Fallback for direct execution / when imported as a top-level module (mcp_server.py
    # adds app/ to sys.path and imports this file without the package prefix)
    from llm_providers import LLMProvider, get_llm_provider

logger = logging.getLogger(__name__)


class NLToSQLConverter:
    """Converts natural language queries to SQL using an LLM provider, falling
    back to simple rule-based pattern matching if no provider is available."""

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        self.llm_provider = llm_provider if llm_provider is not None else get_llm_provider()
        if self.llm_provider is None:
            logger.info("No LLM provider configured (set LLM_PROVIDER). Using rule-based SQL generation.")

    def _create_table_context(self, table_schemas: Dict[str, List[Dict[str, Any]]]) -> str:
        """Fallback table context string, used when no richer schema_context is supplied."""
        context_parts = []

        for table_name, columns in table_schemas.items():
            column_info = []
            for col in columns:
                col_str = f"{col['column_name']} {col['data_type']}"
                if not col['is_nullable']:
                    col_str += " NOT NULL"
                column_info.append(col_str)

            context_parts.append(f"Table {table_name}: {', '.join(column_info)}")

        return " | ".join(context_parts)

    def _rule_based_fallback(self, nl_query: str, table_schemas: Dict[str, List[Dict[str, Any]]]) -> str:
        """Rule-based fallback for SQL generation when no LLM provider is available"""
        nl_lower = nl_query.lower()

        # Get first table as default
        table_names = list(table_schemas.keys())
        if not table_names:
            raise ValueError("No tables available")

        default_table = table_names[0]

        # Simple patterns for common queries
        if any(word in nl_lower for word in ['all', 'everything', 'list', 'show']):
            if 'customers' in nl_lower or 'customer' in nl_lower:
                table = 'customers' if 'customers' in table_names else default_table
            elif 'orders' in nl_lower or 'order' in nl_lower:
                table = 'orders' if 'orders' in table_names else default_table
            else:
                table = default_table
            return f"SELECT * FROM {table}"

        if 'count' in nl_lower:
            if 'customers' in nl_lower:
                table = 'customers' if 'customers' in table_names else default_table
            elif 'orders' in nl_lower:
                table = 'orders' if 'orders' in table_names else default_table
            else:
                table = default_table
            return f"SELECT COUNT(*) as count FROM {table}"

        if any(word in nl_lower for word in ['top', 'first', 'limit']):
            # Extract number if present
            numbers = re.findall(r'\d+', nl_query)
            limit = numbers[0] if numbers else "10"

            if 'customers' in nl_lower:
                table = 'customers' if 'customers' in table_names else default_table
            elif 'orders' in nl_lower:
                table = 'orders' if 'orders' in table_names else default_table
            else:
                table = default_table

            return f"SELECT * FROM {table} LIMIT {limit}"

        # Default fallback
        return f"SELECT * FROM {default_table}"

    async def convert_to_sql(
        self,
        nl_query: str,
        table_schemas: Dict[str, List[Dict[str, Any]]],
        schema_context: Optional[str] = None,
        dialect: str = "SQL",
    ) -> str:
        """Convert natural language query to SQL.

        table_schemas is always required (used by the rule-based fallback to pick
        a default table). schema_context is an optional richer, pre-formatted
        prompt string (e.g. from app.metadata.format_metadata_for_prompt) that,
        when supplied, is what actually gets sent to the LLM instead of the plain
        column list derived from table_schemas.
        """
        try:
            context = schema_context or self._create_table_context(table_schemas)

            if self.llm_provider:
                try:
                    sql = await self.llm_provider.generate_sql(nl_query, context, dialect)
                    sql = self._clean_generated_sql(sql)

                    if sql and self._is_valid_sql(sql):
                        logger.info(f"LLM-generated SQL: {sql}")
                        return sql
                    else:
                        logger.warning("LLM-generated SQL failed validation, falling back to rule-based")

                except Exception as e:
                    logger.error(f"LLM-based conversion failed: {e}")

            # Fallback to rule-based approach
            sql = self._rule_based_fallback(nl_query, table_schemas)
            logger.info(f"Rule-based SQL: {sql}")
            return sql

        except Exception as e:
            logger.error(f"Error converting NL to SQL: {e}")
            raise ValueError(f"Failed to convert query to SQL: {str(e)}")

    def _clean_generated_sql(self, sql: str) -> str:
        """Clean up generated SQL"""
        if not sql:
            return ""

        # Strip markdown code fences some models wrap SQL in despite instructions
        sql = re.sub(r'^```(?:sql)?\s*|\s*```$', '', sql.strip(), flags=re.IGNORECASE)

        # Remove extra whitespace
        sql = ' '.join(sql.split())

        # Remove trailing semicolon
        sql = sql.rstrip(';')

        # Ensure it starts with SELECT
        if not sql.upper().startswith('SELECT'):
            if 'SELECT' in sql.upper():
                # Extract the SELECT part
                select_pos = sql.upper().find('SELECT')
                sql = sql[select_pos:]
            else:
                return ""

        return sql

    def _is_valid_sql(self, sql: str) -> bool:
        """Basic validation of generated SQL"""
        if not sql:
            return False

        sql_upper = sql.upper()

        # Must start with SELECT
        if not sql_upper.startswith('SELECT'):
            return False

        # Must contain FROM
        if 'FROM' not in sql_upper:
            return False

        # Should not contain dangerous operations
        dangerous = ['DROP', 'DELETE', 'INSERT', 'UPDATE', 'ALTER', 'CREATE', 'TRUNCATE']
        for op in dangerous:
            if op in sql_upper:
                return False

        return True
