FROM python:3.12-slim
WORKDIR /app
COPY cisummary/ /app/cisummary/
COPY fixtures/ /app/fixtures/
COPY ci-verify /usr/local/bin/ci-verify
COPY reporter.json /opt/ni/reporter.json
RUN chmod 0755 /usr/local/bin/ci-verify \
 && sha256sum /opt/ni/reporter.json | cut -d' ' -f1 > /opt/ni/reporter.sha256
