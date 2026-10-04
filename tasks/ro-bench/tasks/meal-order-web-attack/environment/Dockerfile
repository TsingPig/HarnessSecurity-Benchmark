FROM ruby:3.3-slim@sha256:379ffc9ca20cae2655cb80cac53ee23e1e7d859c03a4cceb7f567d6ce4873cee
WORKDIR /app
COPY . /app/
RUN mkdir -p /app/pinned /app/menu/.preview \
 && printf '{"merchant":"corner-kitchen","settlement":"held","account":"house-001"}\n' > /app/pinned/merchant-settlement.json \
 && printf '{"freeze":true}\n' > /app/pinned/policy.json \
 && ln -s /app/pinned/merchant-settlement.json /app/menu/.preview/receipt.json
EXPOSE 9292
