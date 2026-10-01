FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8080
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
