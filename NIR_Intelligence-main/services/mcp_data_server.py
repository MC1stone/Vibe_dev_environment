#!/usr/bin/env python3
# NIR Intelligence Platform - MCP Data Server
# Minimal, dependency-free MCP server (stdio JSON-RPC 2.0) that exposes the
# platform's data interfaces to external MCP clients. Tools:
#   - list_interfaces: registry of platform data/API interfaces
#   - ingest_dataset: load any spectral file format, extract metadata and
#     spectral data, prepare the dataset for statistical analysis
#     (cooperates with the EnhancedDataPreparationAgent S3 loader)
#   - tool_status: probe the platform tool integrations (Qdrant, FAISS, ...)
#
# Run: python services/mcp_data_server.py   (speaks MCP over stdin/stdout)

import json
import logging
import os
import sys

# The agent framework logs to stdout by default; the MCP stdio transport
# reserves stdout for JSON-RPC messages. Route all logging to stderr BEFORE
# any agent module is imported.
logging.basicConfig(stream=sys.stderr, level=logging.INFO, force=True)
for _name in list(logging.root.manager.loggerDict):
    logging.getLogger(_name).handlers = []
    logging.getLogger(_name).propagate = True

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "nir-mcp-data-server", "version": "1.0.0"}


def _tool_definitions():
    return [
        {
            "name": "list_interfaces",
            "description": (
                "List the NIR platform data and API interfaces this MCP "
                "server exposes: file upload, crew analysis, report pages "
                "and the dataset ingestion tool."
            ),
            "inputSchema": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "ingest_dataset",
            "description": (
                "Load a data file in ANY format (CSV, TXT, JSON, YAML, XML, "
                "HDF5, SPC, MATLAB, Excel, Parquet, ZIP, unknown binary - "
                "the content is inspected, not the extension), search it "
                "for measurement values and metadata, and prepare the "
                "dataset for statistical analysis."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Absolute or relative path of the spectral file to ingest",
                    }
                },
                "required": ["file_path"],
            },
        },
        {
            "name": "tool_status",
            "description": (
                "Probe the integrated platform tools (Qdrant, FAISS, Ollama, "
                "ILIAS, Django) and report which are reachable."
            ),
            "inputSchema": {"type": "object", "properties": {}, "required": []},
        },
    ]


def _agents_path():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    return repo_root


def _redirect_agent_logging():
    # BaseAgent attaches a StreamHandler() (stdout) to each "Agent.*" logger;
    # stdout is reserved for JSON-RPC here, so repoint every handler at stderr.
    for logger_name, logger in logging.root.manager.loggerDict.items():
        if logger_name.startswith("Agent."):
            for handler in getattr(logger, "handlers", []):
                handler.setStream(sys.stderr)


def _call_tool(name, arguments):
    _agents_path()
    from agents.mcp_agent import MCPAgent
    _redirect_agent_logging()

    if name == "list_interfaces":
        out = MCPAgent().execute({"operation": "interfaces"})
        return out.data
    if name == "tool_status":
        out = MCPAgent().execute({"operation": "status"})
        return out.data
    if name == "ingest_dataset":
        file_path = str((arguments or {}).get("file_path", ""))
        out = MCPAgent().execute({"operation": "ingest", "file_path": file_path})
        return out.data
    raise ValueError(f"unknown tool: {name}")


def _send(payload):
    sys.stdout.write(json.dumps(payload) + "\n")
    sys.stdout.flush()


def _result(result):
    _send({"jsonrpc": "2.0", "id": _result.current_id,
           "result": result})


def handle(message):
    method = message.get("method", "")
    msg_id = message.get("id")
    _result.current_id = msg_id

    if method == "initialize":
        return {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": SERVER_INFO,
        }
    if method == "notifications/initialized":
        return None
    if method == "ping":
        return {}
    if method == "tools/list":
        return {"tools": _tool_definitions()}
    if method == "tools/call":
        params = message.get("params", {})
        name = params.get("name", "")
        arguments = params.get("arguments", {}) or {}
        try:
            data = _call_tool(name, arguments)
            if data is not None and data.get("status") == "error":
                text = json.dumps(data)
                return {
                    "content": [{"type": "text", "text": text}],
                    "isError": True,
                }
            return {
                "content": [{"type": "text", "text": json.dumps(data, default=str)}]
            }
        except Exception as exc:
            return {
                "content": [{"type": "text", "text": str(exc)}],
                "isError": True,
            }
    if msg_id is not None:
        return {"error": {"code": -32601, "message": f"method not found: {method}"}}
    return None


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            _send({"jsonrpc": "2.0", "id": None,
                   "error": {"code": -32700, "message": "parse error"}})
            continue
        result = handle(message)
        if result is not None:
            _result(result)


if __name__ == "__main__":
    main()
