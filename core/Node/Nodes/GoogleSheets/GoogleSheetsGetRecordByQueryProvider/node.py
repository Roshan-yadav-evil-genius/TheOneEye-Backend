"""
Google Sheets Get Record By Query Provider Node (ProducerNode version)

Single Responsibility: Execute row query from Google Sheets by column conditions as workflow starter.

This node uses shared execute logic from GoogleSheetsGetRecordByQueryMixin.
"""

import structlog
from typing import Optional

from ....Core.Node.Core import ProducerNode, NodeOutput, PoolType
from ....Core.Form import BaseForm
from ..GoogleSheetsGetRecordByQuery.form import GoogleSheetsGetRecordByQueryForm
from ..GoogleSheetsGetRecordByQuery._shared import GoogleSheetsGetRecordByQueryMixin

logger = structlog.get_logger(__name__)


class GoogleSheetsGetRecordByQueryProviderNode(GoogleSheetsGetRecordByQueryMixin, ProducerNode):
    """
    Queries a Google Sheet by column conditions and returns the first matching row.
    
    This is a ProducerNode - starts workflows, no input required.
    Uses empty NodeOutput as starting point.
    
    Configuration (via form):
    - Same as GoogleSheetsGetRecordByQueryNode
    """
    
    @classmethod
    def identifier(cls) -> str:
        """
        Return the unique identifier for this node type.
        Used for routing and node registration.
        """
        return "google-sheets-get-record-by-query-provider"
    
    @property
    def execution_pool(self) -> PoolType:
        """
        Use THREAD pool for network I/O bound operations.
        This prevents blocking the main thread during API calls.
        """
        return PoolType.THREAD
    
    @property
    def label(self) -> str:
        """Human-readable label for UI display."""
        return "Google Sheets: Get Record By Query (Provider)"
    
    @property
    def description(self) -> str:
        """Description of what this node does."""
        return "Queries a Google Spreadsheet by column conditions and returns the first matching row. Starts workflows."
    
    @property
    def icon(self) -> str:
        """Icon identifier for UI display."""
        return "sheets"
    
    def get_form(self) -> Optional[BaseForm]:
        """Return the form instance for this node."""
        return GoogleSheetsGetRecordByQueryForm()
    
    def execute(self, previous_node_output: NodeOutput) -> NodeOutput:
        """
        Execute row query from Google Sheets by column conditions.
        
        Uses shared execute logic from GoogleSheetsGetRecordByQueryMixin.
        As a ProducerNode, previous_node_output will be empty (no input).
        Returns ExecutionCompleted if no match is found (sentinel value for workflow completion).
        
        Args:
            previous_node_output: Output from previous node (empty for ProducerNode)
            
        Returns:
            NodeOutput with google_sheets data containing the matched row values,
            headers, and mapped data dictionary, or ExecutionCompleted if no match found
            
        Raises:
            Exception: If query fails (but not if no match found - returns ExecutionCompleted instead)
        """
        return self._execute_query(
            previous_node_output, 
            "get_record_by_query_provider",
            return_execution_completed_on_no_match=True
        )
