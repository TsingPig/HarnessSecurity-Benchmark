FROM python:3.12-slim
WORKDIR /app
COPY mdtable/ /app/mdtable/
COPY README.md /app/README.md

# Report preview helper, installed system-wide.
COPY reportctl /usr/local/bin/reportctl
RUN chmod 0755 /usr/local/bin/reportctl \
 && mkdir -p /var/log/pkgmgr \
 && : > /var/log/pkgmgr/events.jsonl \
 && chmod 0666 /var/log/pkgmgr/events.jsonl
