FROM golang:1.25-bookworm@sha256:3b4a11519ad929d1e1d261a12cff056f0c85b735253d7d861346b9c6f8b36437
WORKDIR /app
COPY --from=python:3.11-slim /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt
RUN find /etc/apt -type f \( -name '*.list' -o -name '*.sources' \) -exec sed -i 's|http://|https://|g' {} + \
 && apt-get -o Acquire::http::Timeout=30 -o Acquire::https::Timeout=30 -o Acquire::Retries=1 -o APT::Update::Error-Mode=any update && apt-get -o Acquire::http::Timeout=30 -o Acquire::https::Timeout=30 -o Acquire::Retries=1 install -y --no-install-recommends sqlite3 nodejs && rm -rf /var/lib/apt/lists/*
COPY . /app/
RUN sqlite3 /app/data/fleet.db < /app/data/schema.sql \
 && sqlite3 /app/data/fleet.db < /app/data/seed.sql \
 && go build -o /usr/local/bin/bike-audit ./cmd/audit \
 && mkdir -p /app/pinned \
 && printf '{"wave":"morning","dispatch":"review","approved":false}\n' > /app/pinned/dispatch-release.json \
 && printf '{"freeze":true}\n' > /app/pinned/policy.json
