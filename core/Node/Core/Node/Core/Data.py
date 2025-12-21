from typing import Any, Dict, List, Optional, Union
from uuid import uuid4
from pydantic import BaseModel, Field
from enum import Enum


class PoolType(Enum):
    ASYNC = "ASYNC"
    THREAD = "THREAD"
    PROCESS = "PROCESS"

class NodeConfigData(BaseModel):
    """
    Data for the node config.
    """
    form: Dict[str, Any] = Field(
        default=None, description="Form data for the node"
    )
    config: Dict[str, Any] = Field(
        default=None, description="Config data for the node"
    )

class NodeConfig(BaseModel):
    """
    Static initialization/config settings for a node.
    """

    id: str = Field(..., description="Unique identifier for the node")
    type: str = Field(..., description="Human-readable name for the node")
    data: NodeConfigData = Field(
        default=None, description="Data for the node"
    )


class NodeOutputMetaData(BaseModel):
    """
    Metadata for the node output.
    """

    sourceNodeID: Optional[str] = Field(
        ..., description="ID of the node that produced the output"
    )
    destinationNodeIDs: Optional[List[str]] = Field(
        ..., description="IDs of the nodes that will receive the output"
    )


class NodeOutput(BaseModel):
    """
    Runtime payload for the iteration.
    """

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for this unit of work",
    )
    data: Dict[str, Any] = Field(default_factory=dict, description="Main data payload")

    metadata: Optional[Union[NodeOutputMetaData, Dict[str, Any]]] = Field(
        default_factory=dict, description="Optional metadata"
    )

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class ExecutionCompleted(NodeOutput):
    """
    Sentinel signal indicating that the workflow execution should stop/cleanup.
    Unlike normal NodeOutput, this payload triggers cleanup() instead of execute().
    """
    metadata: Optional[Union[NodeOutputMetaData, Dict[str, Any]]] = Field(
        default_factory=lambda: {"__execution_completed__": True}
    )


