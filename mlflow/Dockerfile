FROM python:3.11-slim

RUN pip install --no-cache-dir --default-timeout=600 --retries 10 mlflow

EXPOSE 5000

CMD ["mlflow", "server", \
     "--host", "0.0.0.0", "--port", "5000", \
     "--backend-store-uri", "sqlite:////mlflow-data/mlflow.db", \
     "--default-artifact-root", "/mlflow-data/mlruns", \
     "--allowed-hosts", "*"]