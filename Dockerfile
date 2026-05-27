FROM python:3.11-slim

# Node.js 20 (Claude Code CLI + npx Playwright MCP), Chromium, lsof
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl ca-certificates gnupg lsof \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs chromium \
    && rm -rf /var/lib/apt/lists/*

# Wrap system Chromium to add --no-sandbox (required when running as root in Docker)
RUN mv /usr/bin/chromium /usr/bin/chromium-bin && \
    printf '#!/bin/sh\nexec /usr/bin/chromium-bin --no-sandbox "$@"\n' \
        > /usr/bin/chromium && \
    chmod +x /usr/bin/chromium

# Claude Code CLI — drives the browser agent during auto-apply
RUN npm install -g @anthropic-ai/claude-code

# Install applypilot from source
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -e . && \
    pip install --no-cache-dir --no-deps python-jobspy && \
    pip install --no-cache-dir pydantic tls-client requests markdownify regex

# Playwright-managed Chromium (enrichment + PDF generation)
RUN playwright install --with-deps chromium

# Persistent data (profile, DB, resumes, tailored docs, logs) at /data
ENV APPLYPILOT_DIR=/data
ENV CHROME_PATH=/usr/bin/chromium

VOLUME ["/data"]
EXPOSE 8093
ENTRYPOINT ["applypilot"]
CMD ["--help"]
