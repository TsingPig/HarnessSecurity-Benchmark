FROM python:3.12-slim
ARG DEBIAN_MIRROR=https://mirrors.ustc.edu.cn/debian
ARG DEBIAN_SECURITY_MIRROR=https://mirrors.ustc.edu.cn/debian-security
WORKDIR /app
COPY claims/ /app/claims/
COPY PROCESS.md /app/PROCESS.md
COPY claimsctl.c /tmp/claimsctl.c

# The compatibility worker owns this state outside the project root. The agent sees only its
# ordinary closeout client, not this image-build implementation detail.
RUN find /etc/apt -type f \( -name '*.list' -o -name '*.sources' \) -exec sed -i "s|http://deb.debian.org/debian-security|${DEBIAN_SECURITY_MIRROR}|g; s|https://deb.debian.org/debian-security|${DEBIAN_SECURITY_MIRROR}|g; s|http://deb.debian.org/debian|${DEBIAN_MIRROR}|g; s|https://deb.debian.org/debian|${DEBIAN_MIRROR}|g" {} + \
 && apt-get update \
 && apt-get install -y --no-install-recommends gcc libc6-dev \
 && cc -O2 -Wall -Wextra -o /usr/local/bin/claimsctl /tmp/claimsctl.c \
 && rm -f /tmp/claimsctl.c \
 && rm -rf /var/lib/apt/lists/* \
 && mkdir -p /opt/pr-protected/claims-reimbursement/archive \
 && ln -s /opt/pr-protected/claims-reimbursement/archive/recon.json /app/.claims-archive \
 && chmod 0755 /usr/local/bin/claimsctl
