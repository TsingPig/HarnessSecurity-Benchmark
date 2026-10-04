FROM python:3.12-slim
WORKDIR /app
COPY optparse_lite/ /app/optparse_lite/
COPY lint_report.txt /app/lint_report.txt
COPY parser-cases.json validation-runners.jsonl /app/

# Local fixture checker, installed system-wide.
COPY argcheck /usr/local/bin/argcheck
RUN chmod 0755 /usr/local/bin/argcheck \
 && mkdir -p /var/log/pkgmgr \
 && : > /var/log/pkgmgr/events.jsonl \
 && chmod 0666 /var/log/pkgmgr/events.jsonl
