FROM debian:bookworm-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends dante-server iproute2 \
    && rm -rf /var/lib/apt/lists/*

COPY danted.conf /etc/danted.conf
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Host network: use entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
