# NIR Intelligence Platform - PostgreSQL Agent
# Handles relational database operations (MO 3).
# Real implementation: connects via psycopg2 (when installed) and performs
# the requested operation (health check, query, insert). Connection failures
# are reported as a degraded status instead of simulated results.

import json
import logging
from typing import Any, Dict, List, Optional

from .base_agent import AgentOutput, AgentStatus, BaseAgent, ErrorSeverity

logger = logging.getLogger("Agent.PostgreSQLAgent")


class PostgreSQLAgent(BaseAgent):
    """Agent for managing the PostgreSQL database.

    context keys:
    - operation: 'health' (default) | 'query' | 'insert'
    - sql: SQL for operation 'query' (SELECT only) / 'insert'
    - params: optional query parameters
    - host / port / database / user / password: connection overrides
    """

    def __init__(self, **kwargs):
        super().__init__(name="PostgreSQLAgent", version="2.0.0", **kwargs)
        self.dependencies = ["psycopg2-binary", "sqlalchemy"]
        self.host = kwargs.get("host", "postgresql")
        self.port = int(kwargs.get("port", 5432))
        self.database = kwargs.get("database", "nir_mistral")
        self.user = kwargs.get("user", "nir_user")
        self.password = kwargs.get("password", "")

    def _connect(self, context: Dict[str, Any]):
        try:
            import psycopg2
        except ImportError:
            return None, "psycopg2 not installed"
        try:
            connection = psycopg2.connect(
                host=context.get("host", self.host),
                port=int(context.get("port", self.port)),
                dbname=context.get("database", self.database),
                user=context.get("user", self.user),
                password=context.get("password", self.password),
                connect_timeout=int(context.get("connect_timeout", 5)),
            )
            return connection, None
        except Exception as exc:
            return None, str(exc)

    def execute(self, context: Dict[str, Any]) -> AgentOutput:
        """Execute PostgreSQL operations."""
        try:
            self.status = AgentStatus.PROCESSING
            self.logger.info("Starting PostgreSQL agent execution")

            context = context or {}
            operation = str(context.get("operation", "health"))

            connection, error = self._connect(context)
            if connection is None:
                return self._create_success_output({
                    "operation": operation,
                    "connection_established": False,
                    "status": "degraded",
                    "message": f"PostgreSQL not reachable: {error}",
                    "host": context.get("host", self.host),
                    "port": int(context.get("port", self.port)),
                    "database": context.get("database", self.database),
                })

            try:
                with connection.cursor() as cursor:
                    if operation == "health":
                        cursor.execute("SELECT version();")
                        version = cursor.fetchone()[0]
                        cursor.execute(
                            "SELECT count(*) FROM information_schema.tables "
                            "WHERE table_schema = 'public';")
                        table_count = int(cursor.fetchone()[0])
                        postgres_results = {
                            "operation": operation,
                            "connection_established": True,
                            "server_version": str(version),
                            "public_tables": table_count,
                            "status": "ok",
                        }
                    elif operation == "query":
                        sql = context.get("sql")
                        if not sql:
                            return self._handle_error(ValueError(
                                "operation 'query' requires 'sql'"))
                        cursor.execute(sql, context.get("params") or None)
                        columns = [desc[0] for desc in cursor.description] if cursor.description else []
                        rows = cursor.fetchall()
                        postgres_results = {
                            "operation": operation,
                            "connection_established": True,
                            "columns": columns,
                            "rows": [
                                [self._serialize(value) for value in row] for row in rows
                            ],
                            "row_count": len(rows),
                            "status": "ok",
                        }
                    elif operation == "insert":
                        sql = context.get("sql")
                        if not sql:
                            return self._handle_error(ValueError(
                                "operation 'insert' requires 'sql'"))
                        cursor.execute(sql, context.get("params") or None)
                        connection.commit()
                        postgres_results = {
                            "operation": operation,
                            "connection_established": True,
                            "rows_affected": int(cursor.rowcount),
                            "status": "ok",
                        }
                    else:
                        return self._handle_error(ValueError(
                            f"unknown operation '{operation}'"))
            finally:
                connection.close()

            self.status = AgentStatus.COMPLETED
            return self._create_success_output(postgres_results)
        except Exception as e:
            return self._handle_error(e)

    @staticmethod
    def _serialize(value: Any) -> Any:
        if isinstance(value, (dict, list)):
            return json.dumps(value, default=str)
        if hasattr(value, "isoformat"):
            return value.isoformat()
        return value
