import asyncio
import json
import os
import sys

sys.path.append(os.getcwd())

import structlog
from config.logging_config import setup_logging
from Workflow.flow_engine import FlowEngine

logger = structlog.get_logger(__name__)

async def main():
    # Setup logging first
    setup_logging()
    
    try:
        # Load workflow.json from test folder
        workflow_path = os.path.join(os.path.dirname(__file__), "simulate_workflow_auto_shutdown.json")
        with open(workflow_path, "r") as f:
            workflow_data = json.load(f)
            
        orchestrator = FlowEngine()
        
        # Load and initialize workflow
        orchestrator.load_workflow(workflow_data)
        
        # Run Production Mode
        # Note: In a real scenario, this runs indefinitely. 
        # For simulation, we'll let it run for a few seconds then stop.
        
        logger.info("[Simulation] Starting Workflow Simulation (Auto-Shutdown expected)...")
        simulation_task = asyncio.create_task(orchestrator.run_production())
        
        # Await natural completion via Sentinel Pill (triggered by job_limit and propagated via queues)
        await simulation_task
        logger.info("[Simulation] Simulation Completed.")
        
    except Exception as e:
        logger.exception("[Simulation] Error", error=str(e))

if __name__ == "__main__":
    asyncio.run(main())
