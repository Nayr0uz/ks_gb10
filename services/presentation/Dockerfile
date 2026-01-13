FROM python:3.10-slim-buster

WORKDIR /app

COPY services/presentation/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/presentation/main.py .
COPY services/presentation/presentation_service.py .
COPY shared /app/shared

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003"]
