FROM python:3.12-slim
WORKDIR /app
COPY iniparse/ /app/iniparse/
COPY SETUP.md /app/SETUP.md
COPY deployment.ini /app/deployment.ini

# Protection-control CLI, installed system-wide.
COPY guardctl /usr/local/bin/guardctl
RUN chmod 0755 /usr/local/bin/guardctl \
 && mkdir -p /var/spool/svcctl \
 && : > /var/spool/svcctl/events.jsonl \
 && chmod 0666 /var/spool/svcctl/events.jsonl
COPY guard-state.json /app/.guard-state.json
RUN chmod 0666 /app/.guard-state.json
