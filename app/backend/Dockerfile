FROM python:3.11-slim

WORKDIR /app

COPY app/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/backend/ .
COPY app/ui/ /app/ui/
# Website is in a separate repository - not included in open source build

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

