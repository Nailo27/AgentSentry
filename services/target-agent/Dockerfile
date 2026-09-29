FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
COPY target_agent ./target_agent
COPY demo_gateway.py ./
RUN pip install --no-cache-dir .
USER 65532:65532
CMD ["uvicorn", "target_agent.app:app", "--host", "0.0.0.0", "--port", "8000"]

