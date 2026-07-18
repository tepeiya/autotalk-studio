FROM python:3.14-slim

# 系统依赖：ffmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python 依赖
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e .

# 应用代码
COPY app ./app
COPY tests ./tests

# 配置与存储（由 compose 挂载）
# COPY ../config ./config

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
