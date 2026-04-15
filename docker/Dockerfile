FROM ghcr.io/notkeke/discord-bot-yinxi:base

# set timezone
RUN ln -sf /usr/share/zoneinfo/Asia/Taipei /etc/localtime && \
    echo "Asia/Taipei" > /etc/timezone

COPY . .

# 執行
CMD ["uv", "run", "newbot2.py"]