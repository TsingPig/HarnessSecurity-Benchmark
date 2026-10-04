FROM mcr.microsoft.com/dotnet/sdk:9.0-bookworm-slim
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 ca-certificates \
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
