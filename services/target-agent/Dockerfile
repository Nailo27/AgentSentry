FROM python:3.12-slim
# Both Compose services build the same package; each uses a different command.
WORKDIR /app
# Copy project metadata and both Python packages.
COPY pyproject.toml ./
COPY target_agent ./target_agent
COPY gateway ./gateway
COPY demo_gateway.py ./
# Install the complete Python project.
RUN pip install --no-cache-dir .
# Include the real authorization gateway in the container.
COPY gateway ./gateway
# Run the API as an unprivileged container user.
USER 65532:65532
CMD ["uvicorn", "target_agent.app:app", "--host", "0.0.0.0", "--port", "8000"]
