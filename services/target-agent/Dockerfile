FROM python:3.12-slim
# Both Compose services build the same package; each uses a different command.
WORKDIR /app
COPY pyproject.toml ./
COPY target_agent ./target_agent
COPY demo_gateway.py ./
RUN pip install --no-cache-dir .
# Run the API as an unprivileged container user.
USER 65532:65532
CMD ["uvicorn", "target_agent.app:app", "--host", "0.0.0.0", "--port", "8000"]
