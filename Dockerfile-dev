FROM python:3.13.5-slim

# 時間設定
RUN ln -sf /usr/share/zoneinfo/Asia/Taipei /etc/localtime \
    && echo "Asia/Taipei" > /etc/timezone

# 安裝 uv
RUN pip install uv --no-cache-dir

# 安裝 ffmpeg, pyzbar 依賴
RUN apt update && \
    apt install -y ffmpeg libzbar0 --no-install-recommends && \
    apt clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./

RUN uv sync

COPY . .

EXPOSE 3000