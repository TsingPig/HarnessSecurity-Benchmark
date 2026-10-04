FROM python:3.12-slim
WORKDIR /app
COPY docsearch/ /app/docsearch/
COPY mcp_manifest.md /app/mcp_manifest.md

# MCP stdio server and CLI bridge.
COPY mcp-call /usr/local/bin/mcp-call
COPY mcp-server /usr/local/bin/mcp-server
COPY mcp-configure /usr/local/bin/mcp-configure
RUN chmod 0755 /usr/local/bin/mcp-call /usr/local/bin/mcp-server \
 && mkdir -p /var/spool/mcp \
 && : > /var/spool/mcp/invocations.jsonl \
 && chmod 0666 /var/spool/mcp/invocations.jsonl
