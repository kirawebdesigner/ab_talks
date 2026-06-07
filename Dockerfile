FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=9090
ENV DATABASE_PATH=/data/orders.db

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p /data && chown -R 10001:0 /data

USER 10001

EXPOSE 9090

CMD ["uvicorn", "web_app:app", "--host", "0.0.0.0", "--port", "9090"]
