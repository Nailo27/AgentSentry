# AgentSentry dashboard image (UI-01)
#
# WHY A SEPARATE IMAGE FROM THE TARGET AGENT
# ------------------------------------------
# The agent and gateway deliberately share one image, because they are the same
# Python package started with different commands. The dashboard does not share
# it: Streamlit and pandas pull in roughly 200 MB of dependencies that the agent
# and the gateway have no use for. Putting them in the shared image would bloat
# every container in the lab and widen the dependency surface of the two
# services that actually sit on the authorization path.
#
# The base image matches the target agent's python:3.12-slim so the lab runs one
# Python version everywhere. If the agent's base image changes, change this one
# with it.

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# curl is installed for the container health check. Compose's healthcheck runs
# inside the container, so the tool has to exist in the image.
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

# Dependencies are copied and installed before the application code so that
# editing app.py does not invalidate the cached pip layer. This is the single
# biggest factor in how long a rebuild takes during development.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# A glob rather than a list of filenames. An explicit list has to be updated
# every time a module is added, and forgetting leaves an image that builds
# cleanly and then dies at runtime with ModuleNotFoundError -- a failure that
# only shows up once the container starts. The glob matches the service's
# modules and not tests/, which is a subdirectory.
COPY *.py ./

# Run unprivileged, matching the target agent's USER 65532:65532 (the
# conventional "nonroot" uid). /evidence is created and handed to that uid here
# because a volume mounted at a path the container user cannot write to fails
# at runtime with a permission error that is hard to diagnose.
RUN mkdir -p /evidence /app/policy && chown -R 65532:65532 /evidence /app
USER 65532:65532

EXPOSE 8501

# --server.address=0.0.0.0 makes Streamlit listen on all interfaces *inside the
# container*. That is not the same as exposing it to the network: compose
# publishes the port on 127.0.0.1 only, so the dashboard stays on the host.
# headless and gatherUsageStats keep it from trying to open a browser or phone
# home from inside the lab.
CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--browser.gatherUsageStats=false"]
