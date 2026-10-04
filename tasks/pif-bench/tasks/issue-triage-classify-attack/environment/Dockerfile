FROM python:3.12-slim
WORKDIR /app
COPY triage/ /app/triage/
COPY issue_body.md comments.md ci.log attachment.txt collector-context.json /app/
COPY docs/ /app/docs/
COPY mcp/pif-mcp-server.py /usr/local/bin/pif-mcp-server
COPY mcp/pif-mcp-configure.py /usr/local/bin/pif-mcp-configure
COPY mcp/pif-mcp-replies.json /usr/local/share/pif-mcp-replies.json

# Client for the isolated local recorder. No recorder state is mounted here.
COPY incidentctl /usr/local/bin/incidentctl
RUN chmod 0755 /usr/local/bin/incidentctl
