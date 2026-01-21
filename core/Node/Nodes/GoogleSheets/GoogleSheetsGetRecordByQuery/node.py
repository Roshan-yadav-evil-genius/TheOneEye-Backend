"""
Google Sheets Get Record By Query Node (BlockingNode version)

Single Responsibility: Execute row query from Google Sheets by column conditions in mid-workflow.

This node uses shared execute logic from GoogleSheetsGetRecordByQueryMixin.
"""

import structlog
from typing import Optional

from ....Core.Node.Core import BlockingNode, NodeOutput, PoolType
from ....Core.Form import BaseForm
from .form import GoogleSheetsGetRecordByQueryForm
from ._shared import GoogleSheetsGetRecordByQueryMixin

logger = structlog.get_logger(__name__)


class GoogleSheetsGetRecordByQueryNode(GoogleSheetsGetRecordByQueryMixin, BlockingNode):
    """
    Queries a Google Sheet by column conditions and returns the first matching row.
    
    This is a BlockingNode because it performs network I/O that must
    complete before downstream nodes can proceed.
    
    Configuration (via form):
    - google_account: Connected Google account ID
    - spreadsheet: Spreadsheet ID  
    - sheet: Sheet name
    - query_conditions: Jinja template that evaluates to JSON array of conditions
    - header_row: Row containing column headers (default: 1)
    
    Query Conditions Format:
    [
        {
            "column": "Email",
            "value": "{{ data.email }}",
            "operator": "equals",
            "case_sensitive": false
        },
        {
            "column": "Status",
            "value": "Active",
            "operator": "contains",
            "case_sensitive": true
        }
    ]
    
    Output:
    - data.google_sheets.values: List of cell values
    - data.google_sheets.headers: List of column headers
    - data.google_sheets.data: Dict mapping headers to values
    - data.google_sheets.row_number: Matched row number
    - data.google_sheets.sheet_name: Sheet name
    - data.google_sheets.spreadsheet_id: Spreadsheet ID
    """
    
    @classmethod
    def identifier(cls) -> str:
        """
        Return the unique identifier for this node type.
        Used for routing and node registration.
        """
        return "google-sheets-get-record-by-query"
    
    @property
    def execution_pool(self) -> PoolType:
        """
        Use THREAD pool for network I/O bound operations.
        This prevents blocking the async event loop during API calls.
        """
        return PoolType.THREAD
    
    @property
    def label(self) -> str:
        """Human-readable label for UI display."""
        return "Google Sheets: Get Record By Query"
    
    @property
    def description(self) -> str:
        """Description of what this node does."""
        return "Queries a Google Spreadsheet by column conditions and returns the first matching row with header mapping"
    
    @property
    def icon(self) -> str:
        """Icon identifier for UI display."""
        return "sheets"
    
    def get_form(self) -> Optional[BaseForm]:
        """Return the form instance for this node."""
        return GoogleSheetsGetRecordByQueryForm()
    
    async def execute(self, previous_node_output: NodeOutput) -> NodeOutput:
        """
        Execute row query from Google Sheets by column conditions.
        
        Uses shared execute logic from GoogleSheetsGetRecordByQueryMixin.
        
        Args:
            previous_node_output: Output from the previous node in the workflow
            
        Returns:
            NodeOutput with google_sheets data containing the matched row values,
            headers, and mapped data dictionary
            
        Raises:
            Exception: If query fails or no match found
        """
        return await self._execute_query(previous_node_output, "get_record_by_query")

