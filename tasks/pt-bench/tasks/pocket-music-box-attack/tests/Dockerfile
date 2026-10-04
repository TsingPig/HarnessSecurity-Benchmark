FROM python:3.12-slim
WORKDIR /tests
COPY verify.py verifier_common.py test.sh /tests/
RUN chmod 0755 /tests/test.sh && mkdir -p /app /logs/verifier
