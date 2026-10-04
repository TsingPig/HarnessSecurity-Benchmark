FROM node:22-bookworm-slim
WORKDIR /tests
COPY verify.js /tests/verify.js
COPY test.sh /tests/test.sh
RUN chmod 0755 /tests/test.sh && mkdir -p /app /logs/verifier
