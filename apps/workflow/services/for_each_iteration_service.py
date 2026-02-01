"""
ForEach iteration service.

Single Responsibility: Run one or all iterations of a ForEach node.
- Iterate and stop: run subDAG once for the given index, return forEachNode state.
- Execute (full): run subDAG for every item, collect results, return standardized forEachNode.
"""

import asyncio
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add core to path for imports
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
CORE_PATH = BASE_DIR / "core"
if str(CORE_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_PATH))

import structlog
from Node.Core.Node.Core.BaseNode import LoopNode
from Node.Core.Node.Core.Data import NodeOutput

from ..models import WorkFlow, Node
from ..Serializers.WorkFlow import RawWorkFlawSerializer
from .workflow_converter import workflow_converter

logger = structlog.get_logger(__name__)


class ForEachIterationService:
    """Service for running ForEach iterations: single (iterate and stop) or full (execute)."""

    @staticmethod
    def execute_for_each_iteration(
        workflow_id: str,
        node_id: str,
        form_values: Dict[str, Any],
        input_data: Dict[str, Any],
        iteration_index: Optional[int] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Run one iteration of the ForEach node. If iteration_index is not provided,
        derive next index from node.output_data.forEachNode.state.index + 1 (backend is source of truth).

        Steps:
        1. Load workflow, override ForEach node form with form_values.
        2. Load node and previous results/state; if iteration_index is None, set to state.index + 1 (or 0).
        3. Build FlowEngine, run ForEach once to resolve items, run subDAG at that index.
        4. Return forEachNode state and iteration_output.
        """
        try:
            workflow = WorkFlow.objects.get(id=workflow_id)
        except WorkFlow.DoesNotExist:
            return {
                "success": False,
                "error": f"Workflow not found: {workflow_id}",
                "node_id": node_id,
            }

        workflow_config = RawWorkFlawSerializer(workflow).data
        nodes = []
        for n in workflow_config.get("nodes", []):
            n_copy = dict(n)
            if str(n_copy.get("id")) == str(node_id):
                n_copy["form_values"] = form_values
            nodes.append(n_copy)
        workflow_config = {**workflow_config, "nodes": nodes}

        validation = workflow_converter.validate_workflow(workflow_config)
        if not validation.get("is_valid", True):
            return {
                "success": False,
                "error": f"Workflow validation failed: {', '.join(validation.get('errors', []))}",
                "node_id": node_id,
            }

        # Load previous results and state from node's stored output_data (backend is source of truth)
        node = Node.objects.filter(id=node_id, workflow_id=workflow_id).first()
        if node and node.output_data and isinstance(node.output_data, dict):
            for_each_node_stored = node.output_data.get("forEachNode") or {}
            prev = for_each_node_stored.get("results")
            previous_results = list(prev) if isinstance(prev, list) else []
            # Derive next index from state when not provided by client
            if iteration_index is None:
                state = for_each_node_stored.get("state")
                if isinstance(state, dict) and state.get("index") is not None:
                    try:
                        iteration_index = int(state["index"]) + 1
                    except (TypeError, ValueError):
                        iteration_index = 0
                else:
                    iteration_index = 0
        else:
            previous_results = []
            if iteration_index is None:
                iteration_index = 0

        flow_engine_config = workflow_converter.convert_to_flow_engine_format(workflow_config)

        from Workflow.flow_engine import FlowEngine
        from Workflow.execution.api_flow_runner import APIFlowRunner
        from Workflow.execution.pool_executor import PoolExecutor

        engine = FlowEngine(workflow_id=str(workflow_id))
        engine.load_workflow(flow_engine_config)

        flow_node = engine.flow_graph.get_node(node_id)
        if not flow_node:
            return {
                "success": False,
                "error": f"Node not found in graph: {node_id}",
                "node_id": node_id,
            }
        if not isinstance(flow_node.instance, LoopNode):
            return {
                "success": False,
                "error": f"Node {node_id} is not a LoopNode (for-each)",
                "node_id": node_id,
            }

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        executor = PoolExecutor()
        try:
            result = loop.run_until_complete(
                ForEachIterationService._run_one_iteration(
                    engine=engine,
                    flow_node=flow_node,
                    node_id=node_id,
                    form_values=form_values,
                    input_data=input_data,
                    iteration_index=iteration_index,
                    executor=executor,
                    timeout=timeout,
                    previous_results=previous_results,
                )
            )
            return result
        finally:
            executor.shutdown(wait=True)
            loop.close()

    @staticmethod
    async def _run_one_iteration(
        engine: Any,
        flow_node: Any,
        node_id: str,
        form_values: Dict[str, Any],
        input_data: Dict[str, Any],
        iteration_index: int,
        executor: Any,
        timeout: Optional[float] = None,
        previous_results: Optional[List[Any]] = None,
    ) -> Dict[str, Any]:
        """Run ForEach once to get items, then run subDAG once for the given index; merge with previous_results."""
        from Node.Core.Node.Core.Data import NodeOutput

        node_output = NodeOutput(data=input_data)
        try:
            for_each_result = await executor.execute_in_pool(
                flow_node.instance.execution_pool,
                flow_node.instance,
                node_output,
            )
        except Exception as e:
            logger.exception("ForEach node run failed", node_id=node_id, error=str(e))
            for_each_node = {
                "input": [],
                "results": [],
                "state": {"index": iteration_index, "item": None},
            }
            output_data = {**input_data, "forEachNode": for_each_node}
            return {
                "success": False,
                "error": str(e),
                "node_id": node_id,
                "forEachNode": for_each_node,
                "iteration_output": [],
                "output": {"data": output_data},
            }

        items = for_each_result.data.get("items", [])
        for_each_node = {
            "input": items,
            "results": [],
            "state": {"index": iteration_index, "item": None},
        }

        if iteration_index < 0 or iteration_index >= len(items):
            output_data = {**input_data, "forEachNode": for_each_node}
            return {
                "success": False,
                "error": f"iteration_index {iteration_index} out of range [0, {len(items)})",
                "node_id": node_id,
                "forEachNode": for_each_node,
                "iteration_output": [],
                "output": {"data": output_data},
            }

        for_each_node["state"]["item"] = items[iteration_index]

        subdag_list = flow_node.next.get("subdag") or []
        entry_flow_node = subdag_list[0] if subdag_list else None
        if not entry_flow_node:
            output_data = {**input_data, "forEachNode": for_each_node}
            return {
                "success": True,
                "node_id": node_id,
                "forEachNode": for_each_node,
                "iteration_output": [],
                "output": {"data": output_data},
            }

        # Centralized shape: subDAG receives forEachNode (no top-level item/item_index)
        for_each_for_subdag = {
            "input": items,
            "results": list(previous_results) if previous_results else [],
            "state": {"index": iteration_index, "item": items[iteration_index]},
        }
        element_output = NodeOutput(
            id=node_output.id,
            data={**input_data, "forEachNode": for_each_for_subdag},
            metadata=node_output.metadata,
        )

        from Workflow.execution.api_flow_runner import APIFlowRunner
        runner = APIFlowRunner(start_node=entry_flow_node, executor=executor, events=engine.events)
        await runner._init_nodes()
        collected: List[NodeOutput] = await runner.run_subdag_once(entry_flow_node, element_output)
        iteration_output = [o.data for o in collected]

        # One entry per iteration, same as full loop: single sink or list of sink outputs
        one_entry = iteration_output[0] if len(iteration_output) == 1 else iteration_output
        for_each_node["results"] = (previous_results or []) + [one_entry]
        output_data = {**input_data, "forEachNode": for_each_node}

        return {
            "success": True,
            "node_id": node_id,
            "forEachNode": for_each_node,
            "iteration_output": iteration_output,
            "output": {"data": output_data},
        }

    @staticmethod
    def execute_for_each_full(
        workflow_id: str,
        node_id: str,
        form_values: Dict[str, Any],
        input_data: Dict[str, Any],
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Run the full ForEach loop: subDAG for every item, collect results,
        return standardized forEachNode shape (input, results, state).
        Used when user clicks Execute on a ForEach node.
        """
        try:
            workflow = WorkFlow.objects.get(id=workflow_id)
        except WorkFlow.DoesNotExist:
            return {
                "success": False,
                "error": f"Workflow not found: {workflow_id}",
                "node_id": node_id,
            }

        workflow_config = RawWorkFlawSerializer(workflow).data
        nodes = []
        for n in workflow_config.get("nodes", []):
            n_copy = dict(n)
            if str(n_copy.get("id")) == str(node_id):
                n_copy["form_values"] = form_values
            nodes.append(n_copy)
        workflow_config = {**workflow_config, "nodes": nodes}

        validation = workflow_converter.validate_workflow(workflow_config)
        if not validation.get("is_valid", True):
            return {
                "success": False,
                "error": f"Workflow validation failed: {', '.join(validation.get('errors', []))}",
                "node_id": node_id,
            }

        flow_engine_config = workflow_converter.convert_to_flow_engine_format(workflow_config)

        from Workflow.flow_engine import FlowEngine
        from Workflow.execution.pool_executor import PoolExecutor

        engine = FlowEngine(workflow_id=str(workflow_id))
        engine.load_workflow(flow_engine_config)

        flow_node = engine.flow_graph.get_node(node_id)
        if not flow_node:
            return {
                "success": False,
                "error": f"Node not found in graph: {node_id}",
                "node_id": node_id,
            }
        if not isinstance(flow_node.instance, LoopNode):
            return {
                "success": False,
                "error": f"Node {node_id} is not a LoopNode (for-each)",
                "node_id": node_id,
            }

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        executor = PoolExecutor()
        try:
            result = loop.run_until_complete(
                ForEachIterationService._run_full_loop(
                    engine=engine,
                    flow_node=flow_node,
                    node_id=node_id,
                    input_data=input_data,
                    executor=executor,
                    timeout=timeout,
                )
            )
            return result
        finally:
            executor.shutdown(wait=True)
            loop.close()

    @staticmethod
    async def _run_full_loop(
        engine: Any,
        flow_node: Any,
        node_id: str,
        input_data: Dict[str, Any],
        executor: Any,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Run ForEach once to get items, then run subDAG for each item; return aggregated output."""
        node_output = NodeOutput(data=input_data)
        try:
            for_each_result = await executor.execute_in_pool(
                flow_node.instance.execution_pool,
                flow_node.instance,
                node_output,
            )
        except Exception as e:
            logger.exception("ForEach node run failed", node_id=node_id, error=str(e))
            for_each_node = {
                "input": [],
                "results": [],
                "state": {"index": 0, "item": None},
            }
            output_data = {**input_data, "forEachNode": for_each_node}
            return {
                "success": False,
                "error": str(e),
                "node_id": node_id,
                "output": {"data": output_data},
            }

        items = for_each_result.data.get("items", [])
        for_each_node = {
            "input": items,
            "results": [],
            "state": {"index": len(items) - 1, "item": items[-1]} if items else {"index": 0, "item": None},
        }

        subdag_list = flow_node.next.get("subdag") or []
        entry_flow_node = subdag_list[0] if subdag_list else None
        if not entry_flow_node:
            output_data = {**input_data, "forEachNode": for_each_node}
            return {
                "success": True,
                "node_id": node_id,
                "output": {"data": output_data},
            }

        from Workflow.execution.api_flow_runner import APIFlowRunner

        runner = APIFlowRunner(
            start_node=entry_flow_node, executor=executor, events=engine.events
        )
        await runner._init_nodes()

        all_results: List[Any] = []
        try:
            for idx, element in enumerate(items):
                # Centralized shape: subDAG receives forEachNode (no top-level item/item_index)
                for_each_for_subdag = {
                    "input": items,
                    "results": list(all_results),
                    "state": {"index": idx, "item": element},
                }
                element_output = NodeOutput(
                    id=node_output.id,
                    data={**input_data, "forEachNode": for_each_for_subdag},
                    metadata=node_output.metadata,
                )
                collected: List[NodeOutput] = await runner.run_subdag_once(
                    entry_flow_node, element_output
                )
                iteration_data = [o.data for o in collected]
                if len(iteration_data) == 1:
                    all_results.append(iteration_data[0])
                elif iteration_data:
                    all_results.append(iteration_data)
        except Exception as e:
            logger.exception(
                "ForEach full loop iteration failed",
                node_id=node_id,
                error=str(e),
            )
            for_each_node["results"] = all_results
            if all_results:
                last_idx = len(all_results) - 1
                for_each_node["state"] = {
                    "index": last_idx,
                    "item": items[last_idx] if last_idx < len(items) else None,
                }
            output_data = {**input_data, "forEachNode": for_each_node}
            return {
                "success": False,
                "error": str(e),
                "node_id": node_id,
                "output": {"data": output_data},
            }

        for_each_node["results"] = all_results
        aggregated_data = {**input_data, "forEachNode": for_each_node}
        return {
            "success": True,
            "node_id": node_id,
            "output": {"data": aggregated_data},
        }


for_each_iteration_service = ForEachIterationService()
