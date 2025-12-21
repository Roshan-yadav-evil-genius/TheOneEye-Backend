import asyncio
import json
import os
import sys

# Add the current directory to sys.path to ensure imports work
sys.path.append(os.getcwd())

from config.logging_config import setup_logging
from Workflow.flow_engine import FlowEngine


async def main():
    print("--- Starting Reproduction Script ---")
    setup_logging()
    # 1. Load workflow.json from test folder
    try:
        workflow_path = os.path.join(os.path.dirname(__file__), "reproduce_workflow_loading.json")
        with open(workflow_path, "r") as f:
            workflow_data = json.load(f)
        print("Loaded workflow.json")
    except FileNotFoundError:
        print("Error: workflow.json not found")
        return

    # 2. Initialize Orchestrator
    orchestrator = FlowEngine()

    # 3. Load Workflow
    orchestrator.load_workflow(workflow_data)



if __name__ == "__main__":
    asyncio.run(main())
