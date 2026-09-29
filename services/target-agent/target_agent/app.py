import logging
from fastapi import FastAPI
from .gateway import HttpGateway
from .models import AgentRequest, AgentResponse
from .planner import RuleBasedPlanner
from .runtime import AgentRuntime

logging.basicConfig(level=logging.INFO, format="%(message)s")
app = FastAPI(title="AgentSentry Target Agent")
runtime = AgentRuntime(RuleBasedPlanner(), HttpGateway())


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/agent/message", response_model=AgentResponse)
async def message(request: AgentRequest):
    return await runtime.run(request)

