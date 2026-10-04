FROM python:3.12-slim
WORKDIR /app
COPY dedup/ /app/dedup/
COPY dedup_report.txt /app/dedup_report.txt

# Data-store client, installed system-wide. It is a shell program, so the seed step
# invokes it as a program rather than importing it into an interpreter.
COPY dbx /usr/local/bin/dbx
RUN chmod 0755 /usr/local/bin/dbx \
 && mkdir -p /var/spool/svcctl \
 && /usr/local/bin/dbx init \
 && chmod 0666 /app/staging.sqlite3 \
 && : > /var/spool/svcctl/events.jsonl \
 && chmod 0666 /var/spool/svcctl/events.jsonl
