#!/bin/sh
set -eu
MCP_ADAPTER="${MCP_ADAPTER:-gptme}" GPTME_MCP_ENABLED=1 python3 /usr/local/bin/pif-mcp-configure
