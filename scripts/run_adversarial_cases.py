"""Run the checked-in cases using Python; no extra host dependencies required."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/target-agent"))
from target_agent.adversarial_runner import main

if __name__ == "__main__":
    raise SystemExit(main(root=ROOT))
