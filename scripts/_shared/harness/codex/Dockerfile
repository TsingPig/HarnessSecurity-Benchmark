# Harness image for Codex CLI (agent under test), reused across all mechanisms.
#
# Sourcing policy: codex ships as a Rust binary via npm platform packages (no
# runnable source), so we PIN an official release rather than compiling from
# source.  We fetch the pinned tarball once, record its sha256 for provenance,
# then install it.  0.151.0 is the newest stable @openai/codex on npm as of the
# Snapshot cutoff 2026-08-31 (published 2026-08-29).
#
# The image is self-contained: it also carries the verifier runtime
# (python3 + pytest + git) so the throwaway run container (FROM this image) can
# run the task oracles in the same container the agent worked in.
ARG BASE=node:22-bookworm-slim
FROM node:22-bookworm-slim AS node_runtime
FROM ${BASE}

# 信任根：node:*-slim 不自带 ca-certificates（实测 /etc/ssl/certs 为空），而下面的
# RUN 会先把 apt 源从 http 换成 https，缺信任根就会 "Certificate verification
# failed ... No system certificates available"（缓存被清掉后首次真正执行该步骤时暴露）。
# 与 harness/_shared/Dockerfile 保持同一做法：复用 python:3.11-slim 的 CA bundle。
COPY --from=python:3.11-slim /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt

# Add the agent runtime without replacing the task's Python or WORKDIR.
COPY --from=node_runtime /usr/local/bin/node /usr/local/bin/node
COPY --from=node_runtime /usr/local/lib/node_modules/npm /opt/npm
RUN ln -sf /opt/npm/bin/npm-cli.js /usr/local/bin/npm

ARG VERSION=0.151.0
ARG UBUNTU_MIRROR=
ENV DEBIAN_FRONTEND=noninteractive

# Verifier runtime + git, shared by every mechanism's tasks.
# bubblewrap is codex's Linux sandbox backend: without it the run prints
# "could not find bubblewrap on PATH" and `-s workspace-write` is not enforced,
# so writes outside the workspace would go unchecked.
RUN find /etc/apt -type f \( -name '*.list' -o -name '*.sources' \) -exec sed -i 's|http://|https://|g' {} + \
 && if [ -n "$UBUNTU_MIRROR" ]; then find /etc/apt -type f \( -name '*.list' -o -name '*.sources' \) -exec sed -i "s|https://archive.ubuntu.com/ubuntu|${UBUNTU_MIRROR}|g; s|https://security.ubuntu.com/ubuntu|${UBUNTU_MIRROR}|g" {} +; fi \
 && apt-get -o Acquire::http::Timeout=30 -o Acquire::https::Timeout=30 -o Acquire::Retries=1 -o APT::Update::Error-Mode=any update \
 && apt-get -o Acquire::http::Timeout=30 -o Acquire::https::Timeout=30 -o Acquire::Retries=1 install -y --no-install-recommends python3 python3-pytest git ca-certificates bubblewrap \
 && rm -rf /var/lib/apt/lists/*

# Install the pinned wrapper and the required native package with verified integrity.
COPY --from=harness_shared install.py /opt/install.py
ARG INSTALL_KIND=npm
ARG TARBALL=https://registry.npmjs.org/@openai/codex/-/codex-${VERSION}.tgz
ARG INTEGRITY=sha512-mhtWmOZRdmWD1jPbLDnQb59BsaVP/V+lXe/OFNR9ZcLZU0UCiBwn98Fcav1ss7sDIlHkuqj6nWd44IPeXoOhJA==
ARG EXECUTABLE=codex
RUN INSTALL_PREFIX=/usr/local/lib python3 /opt/install.py \
 && NATIVE_NAME="codex-linux-$(node -p process.arch)" \
 && mkdir -p /usr/local/lib/node_modules/@openai/codex/node_modules/@openai \
 && mv "/usr/local/lib/node_modules/@openai/$NATIVE_NAME" "/usr/local/lib/node_modules/@openai/codex/node_modules/@openai/$NATIVE_NAME" \
 && cp /usr/local/lib/provenance.json /opt/codex_provenance.txt \
 && ln -sf /usr/local/lib/node_modules/@openai/codex/bin/codex.js /usr/local/bin/codex \
 && codex --version
