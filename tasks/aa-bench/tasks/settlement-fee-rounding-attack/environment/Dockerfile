FROM python:3.12-slim
WORKDIR /app
COPY billing/ /app/billing/
COPY reconcile_report.txt /app/reconcile_report.txt

# Payments CLI, installed system-wide with its spool directory.
COPY payctl /usr/local/bin/payctl
RUN chmod 0755 /usr/local/bin/payctl \
 && mkdir -p /var/spool/payctl
