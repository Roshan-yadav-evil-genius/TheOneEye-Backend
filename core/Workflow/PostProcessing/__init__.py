from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..flow_graph import FlowGraph


class PostProcessor(ABC):
    """
    Abstract base class for all workflow post-processing operations.
    Follows Single Responsibility Principle - each processor handles one concern.
    """

    def __init__(self, graph: "FlowGraph"):
        """
        Initialize PostProcessor with flow graph.

        Args:
            graph: FlowGraph instance to process
        """
        self.graph = graph

    @abstractmethod
    def execute(self) -> None:
        """
        Execute the post-processing operation on the workflow graph.
        """
        pass
