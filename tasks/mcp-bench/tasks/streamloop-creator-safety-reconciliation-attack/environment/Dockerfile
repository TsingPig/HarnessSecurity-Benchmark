ARG BASE=node:22-bookworm-slim
FROM ${BASE}
WORKDIR /app
COPY --from=python:3.11-slim /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt
RUN find /etc/apt -type f \( -name '*.list' -o -name '*.sources' \) -exec sed -i 's|http://|https://|g' {} + \
 && apt-get -o Acquire::http::Timeout=30 -o Acquire::https::Timeout=30 -o Acquire::Retries=1 -o APT::Update::Error-Mode=any update && apt-get -o Acquire::http::Timeout=30 -o Acquire::https::Timeout=30 -o Acquire::Retries=1 install -y --no-install-recommends python3 sqlite3 \
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
