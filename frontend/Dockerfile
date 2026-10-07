FROM python:3.11-slim

WORKDIR /app
RUN pip install --no-cache-dir --default-timeout=600 --retries 10 streamlit requests

COPY app.py .

EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]