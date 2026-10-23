FROM ghcr.io/notkeke/discord-bot-yinxi:base

ENV PYTHONPYCACHEPREFIX=/tmp/pycache

# set timezone
RUN ln -sf /usr/share/zoneinfo/Asia/Taipei /etc/localtime && \
    echo "Asia/Taipei" > /etc/timezone

WORKDIR /app

COPY . .

# 執行
CMD ["/opt/venv/bin/python", "newbot2.py"]