ARG BASE=node:22-bookworm-slim
FROM node:22-bookworm-slim AS node_runtime
FROM ${BASE}
COPY --from=python:3.11-slim /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt
COPY --from=node_runtime /usr/local/bin/node /usr/local/bin/node
COPY --from=node_runtime /usr/local/lib/node_modules/npm /opt/npm
ARG UBUNTU_MIRROR=
ARG APT_PACKAGES=
RUN ln -sf /opt/npm/bin/npm-cli.js /usr/local/bin/npm \
 && find /etc/apt -type f \( -name '*.list' -o -name '*.sources' \) -exec sed -i 's|http://|https://|g' {} + \
 && if [ -n "$UBUNTU_MIRROR" ]; then find /etc/apt -type f \( -name '*.list' -o -name '*.sources' \) -exec sed -i "s|https://archive.ubuntu.com/ubuntu|${UBUNTU_MIRROR}|g; s|https://security.ubuntu.com/ubuntu|${UBUNTU_MIRROR}|g" {} +; fi \
 && apt-get -o Acquire::http::Timeout=30 -o Acquire::https::Timeout=30 -o Acquire::Retries=1 update \
 && apt-get install -y --no-install-recommends python3 python3-venv python3-pytest git ca-certificates bubblewrap ${APT_PACKAGES} \
 && rm -rf /var/lib/apt/lists/*
COPY --from=harness_source . /opt/build-source
COPY install.py /opt/install.py
ARG INSTALL_KIND
ARG TARBALL
ARG INTEGRITY
ARG EXECUTABLE
ARG SOURCE_SHA256
RUN --mount=type=cache,target=/root/.cache/pip --mount=type=cache,target=/root/.npm python3 /opt/install.py
ENV PATH="/opt/launch/bin:/opt/agent/node_modules/.bin:${PATH}"
