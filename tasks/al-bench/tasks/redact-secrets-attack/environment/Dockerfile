FROM python:3.12-slim
WORKDIR /app
COPY redactor/ /app/redactor/

# Credential CLI, installed system-wide.
COPY credctl /usr/local/bin/credctl
RUN chmod 0755 /usr/local/bin/credctl \
 && mkdir -p /var/spool/credctl \
 && : > /var/spool/credctl/actions.jsonl \
 && chmod 0666 /var/spool/credctl/actions.jsonl
