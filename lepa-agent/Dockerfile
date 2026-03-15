FROM python:3.11-slim
WORKDIR /app/lepa-agent

# Install agent deps
COPY lepa-agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install backend deps (agent imports from lepa-backend)
COPY lepa-backend/requirements.txt /tmp/backend-requirements.txt
RUN pip install --no-cache-dir -r /tmp/backend-requirements.txt

COPY lepa-backend/ /app/lepa-backend/
COPY lepa-agent/ .

EXPOSE 8001
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]
