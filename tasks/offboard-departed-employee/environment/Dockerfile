FROM python:3.12-slim-bookworm

# Create unprivileged user
RUN useradd -m -u 1000 agent

WORKDIR /app

# Copy seed directory and assign ownership
COPY data/ /app/data/
RUN chown -R agent:agent /app

USER agent
