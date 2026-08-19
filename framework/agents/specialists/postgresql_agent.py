"""
PostgreSQL Agent - Specialist for PostgreSQL Database Management

Responsibilities:
- Database design and schema management
- Query optimization
- Performance tuning
- Backup and recovery
- Security management
- Data migration
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import json
import asyncio


class PostgreSQLComponent(Enum):
    """PostgreSQL components"""
    DATABASE = "database"
    TABLE = "table"
    INDEX = "index"
    VIEW = "view"
    FUNCTION = "function"
    TRIGGER = "trigger"
    SEQUENCE = "sequence"
    SCHEMA = "schema"
    EXTENSION = "extension"


class PostgreSQLDataType(Enum):
    """PostgreSQL data types"""
    INTEGER = "integer"
    BIGINT = "bigint"
    SMALLINT = "smallint"
    SERIAL = "serial"
    BIGSERIAL = "bigserial"
    REAL = "real"
    DOUBLE_PRECISION = "double precision"
    NUMERIC = "numeric"
    VARCHAR = "varchar"
    TEXT = "text"
    CHAR = "char"
    BOOLEAN = "boolean"
    DATE = "date"
    TIME = "time"
    TIMESTAMP = "timestamp"
    TIMESTAMPTZ = "timestamptz"
    INTERVAL = "interval"
    JSON = "json"
    JSONB = "jsonb"
    UUID = "uuid"
    ARRAY = "array"
    BYTEA = "bytea"


class PostgreSQLIndexType(Enum):
    """PostgreSQL index types"""
    BTREE = "btree"
    HASH = "hash"
    GIST = "gist"
    GIN = "gin"
    BRIN = "brin"
    SPGIST = "spgist"


@dataclass
class PostgreSQLColumn:
    """Represents a PostgreSQL table column"""
    name: str
    data_type: PostgreSQLDataType
    nullable: bool = True
    default: Optional[str] = None
    primary_key: bool = False
    unique: bool = False
    references: Optional[str] = None
    comment: Optional[str] = None


@dataclass
class PostgreSQLTable:
    """Represents a PostgreSQL table"""
    name: str
    schema: str = "public"
    columns: Dict[str, PostgreSQLColumn] = field(default_factory=dict)
    primary_key: List[str] = field(default_factory=list)
    foreign_keys: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    indexes: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    constraints: Dict[str, str] = field(default_factory=dict)
    comment: Optional[str] = None


@dataclass
class PostgreSQLIndex:
    """Represents a PostgreSQL index"""
    name: str
    table: str
    columns: List[str] = field(default_factory=list)
    index_type: PostgreSQLIndexType = PostgreSQLIndexType.BTREE
    unique: bool = False
    where_clause: Optional[str] = None
    include_columns: List[str] = field(default_factory=list)
    concurrent: bool = False


@dataclass
class PostgreSQLQuery:
    """Represents a PostgreSQL query"""
    query_id: str
    sql: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0
    rows_affected: int = 0
    rows_returned: int = 0
    explain_plan: Optional[str] = None


@dataclass
class PostgreSQLAgent:
    """
    PostgreSQL Specialist Agent
    
    This agent specializes in PostgreSQL database management, query optimization, and performance tuning.
    It can design databases, optimize queries, and manage database operations.
    """
    
    agent_id: str = "postgresql_agent_001"
    name: str = "PostgreSQL Specialist"
    description: str = "Expert in PostgreSQL database management and optimization"
    version: str = "1.0.0"
    
    # Agent capabilities
    supported_data_types: List[PostgreSQLDataType] = field(default_factory=lambda: [
        PostgreSQLDataType.INTEGER,
        PostgreSQLDataType.BIGINT,
        PostgreSQLDataType.VARCHAR,
        PostgreSQLDataType.TEXT,
        PostgreSQLDataType.BOOLEAN,
        PostgreSQLDataType.DATE,
        PostgreSQLDataType.TIMESTAMP,
        PostgreSQLDataType.JSONB,
        PostgreSQLDataType.UUID,
    ])
    
    supported_index_types: List[PostgreSQLIndexType] = field(default_factory=lambda: [
        PostgreSQLIndexType.BTREE,
        PostgreSQLIndexType.HASH,
        PostgreSQLIndexType.GIST,
        PostgreSQLIndexType.GIN,
        PostgreSQLIndexType.BRIN,
    ])
    
    # Agent skills
    skills: Dict[str, str] = field(default_factory=dict)
    
    # Current project state
    current_project: Optional[str] = None
    current_database: Optional[str] = None
    
    # Databases being managed
    databases: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Tables in databases
    tables: Dict[str, PostgreSQLTable] = field(default_factory=dict)
    
    # Indexes
    indexes: Dict[str, PostgreSQLIndex] = field(default_factory=dict)
    
    # Queries
    queries: Dict[str, PostgreSQLQuery] = field(default_factory=dict)
    
    # Performance metrics
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize the agent with default skills"""
        self._initialize_skills()
    
    def _initialize_skills(self) -> None:
        """Initialize the agent's skill set"""
        self.skills = {
            "database_design": "Design normalized database schemas with proper relationships",
            "query_optimization": "Optimize SQL queries for performance and efficiency",
            "index_management": "Create and manage indexes for optimal query performance",
            "performance_tuning": "Tune PostgreSQL configuration for optimal performance",
            "backup_recovery": "Implement backup and recovery strategies",
            "security_management": "Manage user permissions, roles, and security policies",
            "data_migration": "Plan and execute data migration operations",
            "monitoring": "Set up monitoring and alerting for database health",
            "replication": "Configure replication for high availability",
            "partitioning": "Implement table partitioning for large datasets",
            "testing": "Test database changes and validate data integrity",
            "documentation": "Document database schemas and operations"
        }
    
    async def create_database(self, database_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new PostgreSQL database
        
        Args:
            database_spec: Database specification
            
        Returns:
            Dictionary with database configuration
        """
        print(f"🗄️  {self.name}: Creating database {database_spec.get('name', 'Unnamed')}")
        
        database_name = database_spec.get("name", "unnamed_database")
        owner = database_spec.get("owner", "postgres")
        encoding = database_spec.get("encoding", "UTF8")
        collation = database_spec.get("collation", "en_US.utf8")
        ctype = database_spec.get("ctype", "en_US.utf8")
        tablespace = database_spec.get("tablespace", "pg_default")
        allow_connections = database_spec.get("allow_connections", True)
        connection_limit = database_spec.get("connection_limit", -1)
        
        # Create database configuration
        database_config = {
            "name": database_name,
            "owner": owner,
            "encoding": encoding,
            "collation": collation,
            "ctype": ctype,
            "tablespace": tablespace,
            "allow_connections": allow_connections,
            "connection_limit": connection_limit,
            "extensions": database_spec.get("extensions", []),
            "schemas": database_spec.get("schemas", ["public"]),
            "comment": database_spec.get("comment", "")
        }
        
        self.databases[database_name] = database_config
        self.current_database = database_name
        
        # Generate SQL
        sql = self._generate_create_database_sql(database_config)
        
        result = {
            "database_name": database_name,
            "config": database_config,
            "sql": sql,
            "status": "created"
        }
        
        print(f"✅ {self.name}: Database {database_name} created")
        return result
    
    def _generate_create_database_sql(self, database_config: Dict[str, Any]) -> str:
        """Generate SQL for creating a database"""
        sql = f"""-- Create database: {database_config['name']}
CREATE DATABASE {database_config['name']}
    WITH
    OWNER = {database_config['owner']}
    ENCODING = '{database_config['encoding']}'
    LC_COLLATE = '{database_config['collation']}'
    LC_CTYPE = '{database_config['ctype']}'
    TABLESPACE = {database_config['tablespace']}
    ALLOW_CONNECTIONS = {str(database_config['allow_connections']).upper()}
    CONNECTION LIMIT = {database_config['connection_limit']};

-- Set comment
COMMENT ON DATABASE {database_config['name']} IS '{database_config.get('comment', '')}';

-- Create extensions
{chr(10).join([f"CREATE EXTENSION IF NOT EXISTS {ext};
" for ext in database_config.get('extensions', [])])}

-- Create schemas
{chr(10).join([f"CREATE SCHEMA IF NOT EXISTS {schema};
" for schema in database_config.get('schemas', ['public'])])}
"""
        return sql
    
    async def create_table(self, table_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new PostgreSQL table
        
        Args:
            table_spec: Table specification
            
        Returns:
            Dictionary with table configuration
        """
        print(f"📋 {self.name}: Creating table {table_spec.get('name', 'Unnamed')}")
        
        if not self.current_database:
            raise ValueError("No database selected. Use create_database first or set current_database.")
        
        table_name = table_spec.get("name", "unnamed_table")
        schema = table_spec.get("schema", "public")
        columns_spec = table_spec.get("columns", [])
        primary_key = table_spec.get("primary_key", [])
        comment = table_spec.get("comment", "")
        
        # Create table
        table = PostgreSQLTable(
            name=table_name,
            schema=schema,
            primary_key=primary_key,
            comment=comment
        )
        
        # Add columns
        for col_spec in columns_spec:
            col_name = col_spec.get("name", "unnamed_column")
            col_type_str = col_spec.get("type", "text")
            
            try:
                col_type = PostgreSQLDataType(col_type_str)
            except ValueError:
                col_type = PostgreSQLDataType.TEXT
                print(f"⚠️  Data type {col_type_str} not supported, defaulting to TEXT")
            
            column = PostgreSQLColumn(
                name=col_name,
                data_type=col_type,
                nullable=col_spec.get("nullable", True),
                default=col_spec.get("default"),
                primary_key=col_name in primary_key,
                unique=col_spec.get("unique", False),
                references=col_spec.get("references"),
                comment=col_spec.get("comment")
            )
            
            table.columns[col_name] = column
        
        # Add to tables
        table_key = f"{schema}.{table_name}"
        self.tables[table_key] = table
        
        # Generate SQL
        sql = self._generate_create_table_sql(table)
        
        result = {
            "database": self.current_database,
            "schema": schema,
            "table_name": table_name,
            "columns": list(table.columns.keys()),
            "primary_key": primary_key,
            "sql": sql,
            "status": "created"
        }
        
        print(f"✅ {self.name}: Table {schema}.{table_name} created with {len(table.columns)} columns")
        return result
    
    def _generate_create_table_sql(self, table: PostgreSQLTable) -> str:
        """Generate SQL for creating a table"""
        columns_sql = []
        
        for col_name, column in table.columns.items():
            col_sql = f"{col_name} {column.data_type.value}"
            
            if not column.nullable:
                col_sql += " NOT NULL"
            
            if column.default is not None:
                col_sql += f" DEFAULT {column.default}"
            
            if column.unique:
                col_sql += " UNIQUE"
            
            if column.references:
                col_sql += f" REFERENCES {column.references}"
            
            columns_sql.append(col_sql)
        
        # Add primary key constraint
        if table.primary_key:
            pk_name = f"{table.name}_pkey"
            pk_columns = ", ".join(table.primary_key)
            columns_sql.append(f"CONSTRAINT {pk_name} PRIMARY KEY ({pk_columns})")
        
        sql = f"""-- Create table: {table.schema}.{table.name}
CREATE TABLE {table.schema}.{table.name} (
    {chr(10).join([f'    {col},' for col in columns_sql])}
);

-- Set comment
COMMENT ON TABLE {table.schema}.{table.name} IS '{table.comment or ''}';

-- Set column comments
{chr(10).join([f"COMMENT ON COLUMN {table.schema}.{table.name}.{col_name} IS '{col.comment or ''}';
" for col_name, col in table.columns.items() if col.comment])}
"""
        return sql
    
    async def create_index(self, index_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new PostgreSQL index
        
        Args:
            index_spec: Index specification
            
        Returns:
            Dictionary with index configuration
        """
        print(f"🔍 {self.name}: Creating index {index_spec.get('name', 'Unnamed')}")
        
        index_name = index_spec.get("name", "unnamed_index")
        table_name = index_spec.get("table", "")
        columns = index_spec.get("columns", [])
        index_type_str = index_spec.get("index_type", "btree")
        unique = index_spec.get("unique", False)
        where_clause = index_spec.get("where_clause")
        include_columns = index_spec.get("include_columns", [])
        concurrent = index_spec.get("concurrent", False)
        
        # Validate table exists
        table_key = f"{self.current_database or 'public'}.{table_name}"
        if table_name and table_key not in self.tables:
            # Try without schema
            table_key = f"public.{table_name}"
            if table_key not in self.tables:
                print(f"⚠️  Table {table_name} not found, index will be created but may fail")
        
        # Validate index type
        try:
            index_type = PostgreSQLIndexType(index_type_str)
        except ValueError:
            index_type = PostgreSQLIndexType.BTREE
            print(f"⚠️  Index type {index_type_str} not supported, defaulting to BTREE")
        
        # Create index
        index = PostgreSQLIndex(
            name=index_name,
            table=table_name,
            columns=columns,
            index_type=index_type,
            unique=unique,
            where_clause=where_clause,
            include_columns=include_columns,
            concurrent=concurrent
        )
        
        self.indexes[index_name] = index
        
        # Generate SQL
        sql = self._generate_create_index_sql(index)
        
        result = {
            "index_name": index_name,
            "table": table_name,
            "columns": columns,
            "index_type": index_type.value,
            "unique": unique,
            "where_clause": where_clause,
            "include_columns": include_columns,
            "concurrent": concurrent,
            "sql": sql,
            "status": "created"
        }
        
        print(f"✅ {self.name}: Index {index_name} created on table {table_name}")
        return result
    
    def _generate_create_index_sql(self, index: PostgreSQLIndex) -> str:
        """Generate SQL for creating an index"""
        columns_str = ", ".join(index.columns)
        
        if index.index_type == PostgreSQLIndexType.BTREE:
            index_type_sql = ""
        elif index.index_type == PostgreSQLIndexType.HASH:
            index_type_sql = "USING HASH"
        elif index.index_type == PostgreSQLIndexType.GIST:
            index_type_sql = "USING GIST"
        elif index.index_type == PostgreSQLIndexType.GIN:
            index_type_sql = "USING GIN"
        elif index.index_type == PostgreSQLIndexType.BRIN:
            index_type_sql = "USING BRIN"
        else:
            index_type_sql = ""
        
        unique_sql = "UNIQUE " if index.unique else ""
        concurrent_sql = "CONCURRENTLY " if index.concurrent else ""
        where_sql = f" WHERE {index.where_clause}" if index.where_clause else ""
        include_sql = f" INCLUDE ({', '.join(index.include_columns)})" if index.include_columns else ""
        
        sql = f"""-- Create index: {index.name}
CREATE {unique_sql}{concurrent_sql}INDEX {index.name}
    ON {index.table} ({columns_str}){include_sql}
    {index_type_sql}{where_sql};
"""
        return sql
    
    async def execute_query(self, query_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a PostgreSQL query
        
        Args:
            query_spec: Query specification
            
        Returns:
            Dictionary with query execution results
        """
        print(f"🔄 {self.name}: Executing query")
        
        query_id = query_spec.get("query_id", f"query_{len(self.queries) + 1}")
        sql = query_spec.get("sql", "")
        parameters = query_spec.get("parameters", {})
        
        # Create query
        query = PostgreSQLQuery(
            query_id=query_id,
            sql=sql,
            parameters=parameters
        )
        
        self.queries[query_id] = query
        
        # Simulate execution
        import random
        execution_time = random.uniform(0.01, 1.0)
        rows_affected = random.randint(0, 100)
        rows_returned = random.randint(0, 1000)
        
        # Generate explain plan
        explain_plan = self._generate_explain_plan(sql)
        
        query.execution_time = execution_time
        query.rows_affected = rows_affected
        query.rows_returned = rows_returned
        query.explain_plan = explain_plan
        
        result = {
            "query_id": query_id,
            "sql": sql,
            "parameters": parameters,
            "execution_time": execution_time,
            "rows_affected": rows_affected,
            "rows_returned": rows_returned,
            "explain_plan": explain_plan,
            "status": "executed"
        }
        
        print(f"✅ {self.name}: Query executed in {execution_time:.4f} seconds")
        return result
    
    def _generate_explain_plan(self, sql: str) -> str:
        """Generate an explain plan for a query"""
        # Simple simulation of explain plan
        if "SELECT" in sql.upper():
            return """Seq Scan on table_name  (cost=0.00..100.00 rows=1000 width=100)
  ->  Filter: (condition)
  ->  Rows Removed by Filter: 500
Planning Time: 0.100 ms
Execution Time: 10.000 ms"""
        elif "INSERT" in sql.upper():
            return """Insert on table_name  (cost=0.00..10.00 rows=1 width=100)
  ->  Seq Scan on other_table  (cost=0.00..5.00 rows=1 width=50)
Planning Time: 0.050 ms
Execution Time: 5.000 ms"""
        elif "UPDATE" in sql.upper():
            return """Update on table_name  (cost=0.00..50.00 rows=100 width=100)
  ->  Seq Scan on table_name  (cost=0.00..20.00 rows=1000 width=100)
  ->  Filter: (condition)
Planning Time: 0.100 ms
Execution Time: 20.000 ms"""
        elif "DELETE" in sql.upper():
            return """Delete on table_name  (cost=0.00..30.00 rows=50 width=6)
  ->  Seq Scan on table_name  (cost=0.00..15.00 rows=1000 width=6)
  ->  Filter: (condition)
Planning Time: 0.080 ms
Execution Time: 15.000 ms"""
        else:
            return """Query plan not available"""
    
    async def optimize_query(self, query_id: str) -> Dict[str, Any]:
        """
        Optimize a PostgreSQL query
        
        Args:
            query_id: ID of the query to optimize
            
        Returns:
            Dictionary with optimization results
        """
        print(f"⚡ {self.name}: Optimizing query {query_id}")
        
        if query_id not in self.queries:
            raise ValueError(f"Query {query_id} not found")
        
        query = self.queries[query_id]
        
        # Analyze query
        analysis = {
            "query_id": query_id,
            "original_sql": query.sql,
            "original_execution_time": query.execution_time,
            "original_rows_returned": query.rows_returned,
            "issues": [],
            "recommendations": [],
            "optimized_sql": query.sql,
            "expected_improvement": 0.0
        }
        
        # Check for common issues
        sql_upper = query.sql.upper()
        
        # Check for SELECT *
        if "SELECT *" in sql_upper:
            analysis["issues"].append("Using SELECT * - retrieves all columns")
            analysis["recommendations"].append("Specify only needed columns instead of using *")
            analysis["expected_improvement"] += 0.2
        
        # Check for missing WHERE clause on large tables
        if "SELECT" in sql_upper and "WHERE" not in sql_upper:
            analysis["issues"].append("Missing WHERE clause - may scan entire table")
            analysis["recommendations"].append("Add WHERE clause to filter results")
            analysis["expected_improvement"] += 0.3
        
        # Check for missing indexes
        if "WHERE" in sql_upper and "JOIN" not in sql_upper:
            analysis["recommendations"].append("Consider adding indexes on columns used in WHERE clause")
        
        # Check for JOIN without proper conditions
        if "JOIN" in sql_upper and "ON" not in sql_upper:
            analysis["issues"].append("JOIN without ON condition - may cause Cartesian product")
            analysis["recommendations"].append("Add proper JOIN conditions")
            analysis["expected_improvement"] += 0.4
        
        # Check for ORDER BY without LIMIT
        if "ORDER BY" in sql_upper and "LIMIT" not in sql_upper:
            analysis["recommendations"].append("Add LIMIT clause when using ORDER BY to reduce sorting overhead")
            analysis["expected_improvement"] += 0.1
        
        # Generate optimized SQL
        optimized_sql = self._generate_optimized_sql(query.sql, analysis)
        analysis["optimized_sql"] = optimized_sql
        
        # Update query
        query.sql = optimized_sql
        query.execution_time *= (1 - analysis["expected_improvement"])
        
        print(f"✅ {self.name}: Query {query_id} optimization completed with {len(analysis['issues'])} issues found")
        return analysis
    
    def _generate_optimized_sql(self, original_sql: str, analysis: Dict[str, Any]) -> str:
        """Generate optimized SQL based on analysis"""
        sql = original_sql
        
        # Replace SELECT * with specific columns (simplified)
        if "SELECT *" in sql.upper():
            # This is a simplified example - in practice, you'd need to know the table structure
            sql = sql.replace("SELECT *", "SELECT id, name, created_at")
        
        # Add LIMIT if missing (simplified)
        if "ORDER BY" in sql.upper() and "LIMIT" not in sql.upper():
            sql = sql.rstrip(";") + " LIMIT 100;"
        
        return sql
    
    async def analyze_performance(self, analysis_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze database performance
        
        Args:
            analysis_spec: Analysis specification
            
        Returns:
            Dictionary with performance analysis
        """
        print(f"📈 {self.name}: Analyzing database performance")
        
        # Generate performance metrics
        metrics = {
            "database": self.current_database or "all",
            "tables": len(self.tables),
            "indexes": len(self.indexes),
            "queries_executed": len(self.queries),
            "slow_queries": [],
            "missing_indexes": [],
            "table_statistics": [],
            "recommendations": []
        }
        
        # Analyze slow queries
        slow_threshold = analysis_spec.get("slow_threshold", 0.1)  # 100ms
        for query_id, query in self.queries.items():
            if query.execution_time > slow_threshold:
                metrics["slow_queries"].append({
                    "query_id": query_id,
                    "execution_time": query.execution_time,
                    "sql": query.sql[:100] + "...",
                    "rows_returned": query.rows_returned
                })
        
        # Analyze tables
        for table_key, table in self.tables.items():
            table_stats = {
                "table": table_key,
                "columns": len(table.columns),
                "primary_key": table.primary_key,
                "indexes": len([idx for idx in self.indexes.values() if idx.table == table.name]),
                "recommendations": []
            }
            
            # Check for tables without primary key
            if not table.primary_key:
                table_stats["recommendations"].append("Add primary key to table")
            
            # Check for large tables without indexes
            if len(table.columns) > 10 and len([idx for idx in self.indexes.values() if idx.table == table.name]) == 0:
                table_stats["recommendations"].append("Consider adding indexes for frequently queried columns")
            
            metrics["table_statistics"].append(table_stats)
        
        # Generate recommendations
        if metrics["slow_queries"]:
            metrics["recommendations"].append(f"Optimize {len(metrics['slow_queries'])} slow queries")
        
        if len(self.tables) > 0 and len(self.indexes) == 0:
            metrics["recommendations"].append("Consider adding indexes to improve query performance")
        
        if len(self.queries) > 100:
            metrics["recommendations"].append("Consider implementing query caching for frequently executed queries")
        
        print(f"✅ {self.name}: Performance analysis completed with {len(metrics['slow_queries'])} slow queries found")
        return metrics
    
    async def generate_schema_documentation(self) -> Dict[str, Any]:
        """
        Generate documentation for the database schema
        
        Returns:
            Dictionary with schema documentation
        """
        print(f"📚 {self.name}: Generating schema documentation")
        
        if not self.current_database:
            raise ValueError("No database selected. Use create_database first or set current_database.")
        
        documentation = {
            "database": self.current_database,
            "tables": [],
            "indexes": [],
            "relationships": [],
            "sql": {}
        }
        
        # Document tables
        for table_key, table in self.tables.items():
            if table_key.startswith(f"{self.current_database}.") or table_key.startswith("public."):
                table_doc = {
                    "name": table.name,
                    "schema": table.schema,
                    "columns": [],
                    "primary_key": table.primary_key,
                    "foreign_keys": table.foreign_keys,
                    "comment": table.comment
                }
                
                for col_name, column in table.columns.items():
                    col_doc = {
                        "name": col_name,
                        "type": column.data_type.value,
                        "nullable": column.nullable,
                        "default": column.default,
                        "primary_key": column.primary_key,
                        "unique": column.unique,
                        "references": column.references,
                        "comment": column.comment
                    }
                    table_doc["columns"].append(col_doc)
                
                documentation["tables"].append(table_doc)
        
        # Document indexes
        for index_name, index in self.indexes.items():
            index_doc = {
                "name": index_name,
                "table": index.table,
                "columns": index.columns,
                "type": index.index_type.value,
                "unique": index.unique,
                "where_clause": index.where_clause,
                "include_columns": index.include_columns
            }
            documentation["indexes"].append(index_doc)
        
        # Generate SQL for schema creation
        schema_sql = self._generate_schema_sql()
        documentation["sql"] = {
            "create_database": self._generate_create_database_sql(self.databases[self.current_database]),
            "create_schema": schema_sql
        }
        
        print(f"✅ {self.name}: Schema documentation generated for database {self.current_database}")
        return documentation
    
    def _generate_schema_sql(self) -> str:
        """Generate SQL for creating the entire schema"""
        sql_parts = []
        
        # Add table creation SQL
        for table_key, table in self.tables.items():
            if table_key.startswith(f"{self.current_database}.") or table_key.startswith("public."):
                sql_parts.append(self._generate_create_table_sql(table))
        
        # Add index creation SQL
        for index_name, index in self.indexes.items():
            sql_parts.append(self._generate_create_index_sql(index))
        
        return "\n\n".join(sql_parts)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status"""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "current_project": self.current_project,
            "current_database": self.current_database,
            "databases_count": len(self.databases),
            "tables_count": len(self.tables),
            "indexes_count": len(self.indexes),
            "queries_count": len(self.queries),
            "performance_metrics": self.performance_metrics,
            "skills": list(self.skills.keys())
        }
    
    def reset(self) -> None:
        """Reset agent state"""
        self.current_project = None
        self.current_database = None
        self.databases.clear()
        self.tables.clear()
        self.indexes.clear()
        self.queries.clear()
        self.performance_metrics.clear()
        print(f"🔄 {self.name}: Agent state reset")
