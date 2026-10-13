FROM mcr.microsoft.com/dotnet/sdk:9.0-bookworm-slim
COPY --from=python:3.11-slim /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt
RUN find /etc/apt -type f \( -name '*.list' -o -name '*.sources' \) -exec sed -i 's|http://|https://|g' {} + \
 && apt-get -o Acquire::http::Timeout=30 -o Acquire::https::Timeout=30 -o Acquire::Retries=1 -o APT::Update::Error-Mode=any update \
 && apt-get -o Acquire::http::Timeout=30 -o Acquire::https::Timeout=30 -o Acquire::Retries=1 install -y --no-install-recommends python3 ca-certificates \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY GridQuest.csproj NuGet.Config studioctl /app/
COPY community-pack/README.md community-pack/playtest-summary.md community-pack/release-checklist.md community-pack/migration-register.md /app/community-pack/
COPY community-pack/levels/ /app/community-pack/levels/
COPY src/ /app/src/
COPY mcp/pif-mcp-server.py /usr/local/bin/pif-mcp-server
COPY mcp/pif-mcp-configure.py /usr/local/bin/pif-mcp-configure
COPY mcp/pif-mcp-replies.json /usr/local/share/pif-mcp-replies.json
COPY studioctl /usr/local/bin/studioctl
RUN chmod 0755 /usr/local/bin/studioctl
