from abc import ABC, abstractmethod
from typing import Optional

from Node.Core.Form.Core.BaseForm import BaseForm

from .Data import NodeOutput


class BaseNodeMethod(ABC):
    
    async def setup(self):
        """
        setup method is not utilized directly but is called by init method.
        This method is used to initialize the node and set up any necessary resources.
        Default implementation does nothing.
        """
        pass

    async def init(self):
        """
        Before the Loop Manager starts the loop, the init method is called.
        """
        pass

    @abstractmethod
    async def execute(self, previous_node_output: NodeOutput) -> NodeOutput:
        """
        Execute the node logic.
        """
        pass

    async def cleanup(self):
        """
        After the Loop Manager finishes the loop, the cleanup method is called.
        This method is used to clean up any necessary resources.
        Default implementation does nothing.
        """
        pass

    def get_form(self) -> Optional[BaseForm]:
        """
        Get the associated form for this node.
        Default implementation returns None.

        Returns:
            BaseForm: An instance of the form corresponding to this node, or None.
        """
        return None