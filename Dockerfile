FROM python:3.12-slim-bookworm

WORKDIR /app

# iputils-ping: ICMP reachability checks for /ping. Setcap'd, no root needed.
RUN apt-get update \
    && apt-get install -y --no-install-recommends iputils-ping \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    "python-telegram-bot>=22,<23" \
    "python-telegram-bot[socks]" \
    yeelight \
    wakeonlan \
    httpx

COPY smart_home_controller_tg.py smart_home_controller_support.py ./

ENV PYTHONUNBUFFERED=1

CMD ["python", "smart_home_controller_tg.py"]
