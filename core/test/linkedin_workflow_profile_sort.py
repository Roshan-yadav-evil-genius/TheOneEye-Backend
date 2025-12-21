import asyncio
import json
import os
import sys

sys.path.append(os.getcwd())

import structlog
from config.logging_config import setup_logging
from Workflow.flow_engine import FlowEngine
from Node.Nodes.Browser._shared.BrowserManager import BrowserManager

logger = structlog.get_logger(__name__)

async def main():
    # Setup logging first
    setup_logging()
    
    try:
        # Load workflow.json from test folder
        workflow_path = os.path.join(os.path.dirname(__file__), "linkedin_workflow_profile_sort.json")
        with open(workflow_path, "r") as f:
            workflow_data = json.load(f)
            
        orchestrator = FlowEngine()
        
        # Load and initialize workflow
        orchestrator.load_workflow(workflow_data)
        
        # Run Production Mode
        logger.info("[Simulation] Starting Linkedin Workflow Simulation...")
        simulation_task = asyncio.create_task(orchestrator.run_production())
        
        # Await natural completion (StringIterator emits ExecutionCompleted when done)
        await simulation_task
        logger.info("[Simulation] Simulation Completed.")
        
    except Exception as e:
        logger.exception("[Simulation] Error", error=str(e))
    finally:
        # Ensure resources are cleaned up
        await BrowserManager().close()

if __name__ == "__main__":
    asyncio.run(main())
