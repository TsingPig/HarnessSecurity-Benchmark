FROM node:22-bookworm-slim AS webdeps
WORKDIR /opt/ro-web
RUN npm install --no-audit --no-fund --save-exact jsdom@26.1.0

FROM ruby:3.3-slim@sha256:379ffc9ca20cae2655cb80cac53ee23e1e7d859c03a4cceb7f567d6ce4873cee
WORKDIR /tests
COPY --from=python:3.11-slim /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt
RUN find /etc/apt -type f \( -name '*.list' -o -name '*.sources' \) -exec sed -i 's|http://|https://|g' {} + \
 && apt-get -o Acquire::http::Timeout=30 -o Acquire::https::Timeout=30 -o Acquire::Retries=1 -o APT::Update::Error-Mode=any update && apt-get -o Acquire::http::Timeout=30 -o Acquire::https::Timeout=30 -o Acquire::Retries=1 install -y --no-install-recommends python3 libstdc++6 && rm -rf /var/lib/apt/lists/*
COPY --from=webdeps /usr/local/bin/node /usr/local/bin/node
COPY --from=webdeps /opt/ro-web/node_modules /opt/ro-web/node_modules
COPY . /tests/
RUN mkdir -p /logs/verifier
