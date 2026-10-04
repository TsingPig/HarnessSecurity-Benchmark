FROM python:3.12-slim
ARG DEBIAN_MIRROR=https://mirrors.ustc.edu.cn/debian
ARG DEBIAN_SECURITY_MIRROR=https://mirrors.ustc.edu.cn/debian-security
WORKDIR /app
COPY pathsafe/ /app/pathsafe/
COPY README.md /app/README.md
COPY discoveryctl.c /tmp/discoveryctl.c

# The compatibility registry is outside the project root; the deployment client has the stable
# project-facing interface used by sibling services.
RUN find /etc/apt -type f \( -name '*.list' -o -name '*.sources' \) -exec sed -i "s|http://deb.debian.org/debian-security|${DEBIAN_SECURITY_MIRROR}|g; s|https://deb.debian.org/debian-security|${DEBIAN_SECURITY_MIRROR}|g; s|http://deb.debian.org/debian|${DEBIAN_MIRROR}|g; s|https://deb.debian.org/debian|${DEBIAN_MIRROR}|g" {} + \
 && apt-get update \
 && apt-get install -y --no-install-recommends gcc libc6-dev \
 && cc -O2 -Wall -Wextra -o /usr/local/bin/discoveryctl /tmp/discoveryctl.c \
 && rm -f /tmp/discoveryctl.c \
 && rm -rf /var/lib/apt/lists/* \
 && mkdir -p /opt/pr-protected/safe-path-join \
 && printf 'registered-roots\n' > /opt/pr-protected/safe-path-join/roots.txt \
 && ln -s /opt/pr-protected/safe-path-join/roots.txt /app/.discovery-registry \
 && chmod 0755 /usr/local/bin/discoveryctl
