ARG BASE=node:22-bookworm-slim
FROM ${BASE}
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends python3 sqlite3 \
 && rm -rf /var/lib/apt/lists/*
COPY package.json /opt/mcp/package.json
RUN npm --prefix /opt/mcp install --omit=dev --ignore-scripts=false \
 && node -e "const p=require('/opt/mcp/node_modules/mcp-sqlite/package.json'); if(p.version !== '1.0.9') process.exit(1)"
COPY seed_streamloop.py /usr/local/bin/seed-streamloop
COPY fixtures/ /opt/streamloop-fixtures/
COPY mcp-server /usr/local/bin/mcp-server
COPY mcp-configure /usr/local/bin/mcp-configure
COPY src/ /app/src/
RUN mkdir -p /app/reports /opt/streamloop \
 && python3 /usr/local/bin/seed-streamloop /opt/streamloop/streamloop.db /opt/streamloop-fixtures \
 && chmod 0755 /usr/local/bin/mcp-server
