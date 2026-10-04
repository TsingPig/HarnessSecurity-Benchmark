FROM mcr.microsoft.com/dotnet/sdk:9.0-bookworm-slim
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 ca-certificates \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /tests
COPY . /tests/
RUN mkdir -p /app /logs/verifier
