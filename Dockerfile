FROM python:3.14.2
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app
RUN apt-get update && apt-get install -y \
  build-essential && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv
ENV UV_SYSTEM_PYTHON=1

COPY pyproject.toml uv.lock /app/
RUN uv sync --frozen

COPY . /app/

ARG JWT_PRIVATE_KEY_B64=""
ARG JWT_PUBLIC_KEY_B64=""

RUN mkdir -p /var/log/vs-auth
RUN mkdir -p /app/storage/

RUN mkdir -p /app/src/config/ \
  && if [ -n "${JWT_PRIVATE_KEY_B64}" ]; then printf '%s' "$JWT_PRIVATE_KEY_B64" | base64 -d > /app/src/config/_private.pem; fi \
  && if [ -n "${JWT_PUBLIC_KEY_B64}" ]; then printf '%s' "$JWT_PUBLIC_KEY_B64" | base64 -d > /app/src/config/_pub.pem; fi

RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
