FROM python:3.12-slim

WORKDIR /app

# 系统依赖保持最小；构建工具仅编译期需要
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv && uv sync --frozen --no-dev --compile-bytecode

COPY . .

EXPOSE 8000

CMD ["uv", "run", "--no-dev", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
