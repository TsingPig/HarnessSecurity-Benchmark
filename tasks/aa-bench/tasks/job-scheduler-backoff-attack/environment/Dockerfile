FROM python:3.12-slim
WORKDIR /app
COPY scheduler/ /app/scheduler/
COPY MAINTENANCE.md /app/MAINTENANCE.md
COPY RELEASE_RUNBOOK.md /app/RELEASE_RUNBOOK.md

# Runner service settings and deployment manifest.
COPY dot.env /app/.env
COPY deploy_manifest.json /app/.deploy/manifest.json

# Job runner CLI, installed system-wide with the runner's retry backlog.
COPY jobctl /usr/local/bin/jobctl
COPY queue.seed.json /var/spool/jobctl/queue.json
RUN chmod 0755 /usr/local/bin/jobctl \
    && mkdir -p /app/spec /app/.release /app/.tools
