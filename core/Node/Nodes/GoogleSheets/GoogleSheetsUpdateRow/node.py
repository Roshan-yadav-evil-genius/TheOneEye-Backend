"""
Google Sheets Update Row Node

Single Responsibility: Execute row update to Google Sheets.

This node handles:
- Form value extraction
- Calling GoogleSheetsService to update row data
- Formatting output with update results
"""

import structlog
from typing import Optional

from ....Core.Node.Core import BlockingNode, NodeOutput, PoolType
from ....Core.Form import BaseForm
from .form import GoogleSheetsUpdateRowForm
from .._shared.google_sheets_service import GoogleSheetsService

logger = structlog.get_logger(__name__)


class GoogleSheetsUpdateRowNode(BlockingNode):
    """
    Updates a specific row in a Google Sheet.
    
    This is a BlockingNode because it performs network I/O that must
    complete before downstream nodes can proceed.
    
    Configuration (via form):
    - google_account: Connected Google account ID
    - spreadsheet: Spreadsheet ID  
    - sheet: Sheet name
    - row_number: Row to update (1-indexed)
    - row_data: JSON object mapping headers to values
    - header_row: Row containing column headers (default: 1)
    
    Output:
    - data.google_sheets.updated_cells: Number of cells updated
    - data.google_sheets.updated_range: Range that was updated
    - data.google_sheets.row_number: Updated row number
    - data.google_sheets.matched_headers: List of headers that were matched
    - data.google_sheets.sheet_name: Sheet name
    - data.google_sheets.spreadsheet_id: Spreadsheet ID
    """
    
    @classmethod
    def identifier(cls) -> str:
        """
        Return the unique identifier for this node type.
        Used for routing and node registration.
        """
        return "google-sheets-update-row"
    
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
        return "Google Sheets: Update Row"
    
    @property
    def description(self) -> str:
        """Description of what this node does."""
        return "Updates a specific row in a Google Spreadsheet using header mapping"
    
    @property
    def icon(self) -> str:
        """Icon identifier for UI display."""
        return "sheets"
    
    def get_form(self) -> Optional[BaseForm]:
        """Return the form instance for this node."""
        return GoogleSheetsUpdateRowForm()
    
    def execute(self, previous_node_output: NodeOutput) -> NodeOutput:
        """
        Execute row update to Google Sheets.
        
        Args:
            previous_node_output: Output from the previous node in the workflow
            
        Returns:
            NodeOutput with google_sheets data containing the update results
            
        Raises:
            Exception: If row update fails
        """
        # Extract form values
        account_id = self.form.cleaned_data.get('google_account')
        spreadsheet_id = self.form.cleaned_data.get('spreadsheet')
        sheet_name = self.form.cleaned_data.get('sheet')
        row_number = self.form.cleaned_data.get('row_number')
        row_data = self.form.cleaned_data.get('row_data')  # Already parsed as dict
        header_row = self.form.cleaned_data.get('header_row', 1)
        
        logger.info(
            "Updating Google Sheet row",
            node_id=self.node_config.id,
            spreadsheet_id=spreadsheet_id,
            sheet_name=sheet_name,
            row_number=row_number,
            header_row=header_row,
            data_keys=list(row_data.keys()) if row_data else []
        )
        
        try:
            # Create service instance with the selected account
            service = GoogleSheetsService(account_id)
            
            # Update row data with header mapping
            update_result = service.update_row_by_headers(
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name,
                row_number=row_number,
                data=row_data,
                header_row=header_row
            )
            
            logger.info(
                "Row updated successfully",
                node_id=self.node_config.id,
                updated_cells=update_result.get('updated_cells', 0),
                matched_headers=update_result.get('matched_headers', [])
            )
            
            # Attach result to output data with unique key
            output_key = self.get_unique_output_key(previous_node_output, 'google_sheets')
            previous_node_output.data[output_key] = update_result
            
            # Return NodeOutput with metadata
            return NodeOutput(
                id=previous_node_output.id,
                data=previous_node_output.data,
                metadata={
                    "sourceNodeID": self.node_config.id,
                    "sourceNodeName": self.node_config.type,
                    "operation": "update_row",
                    "spreadsheet_id": spreadsheet_id,
                    "sheet_name": sheet_name,
                    "row_number": row_number,
                    "header_row": header_row,
                    "updated_cells": update_result.get('updated_cells', 0)
                }
            )
            
        except Exception as e:
            error_msg = str(e)
            
            # Check if it's a token expiration error
            if 'expired' in error_msg.lower() or 'revoked' in error_msg.lower() or 'invalid_grant' in error_msg.lower():
                logger.error(
                    "Google account token expired or revoked",
                    node_id=self.node_config.id,
                    spreadsheet_id=spreadsheet_id,
                    account_id=account_id,
                    error=error_msg
                )
                raise Exception(
                    f"Google account authentication failed: Your Google account token has expired or been revoked. "
                    f"Please reconnect your Google account in the account settings and try again. "
                    f"Original error: {error_msg}"
                )
            
            logger.error(
                "Failed to update row",
                node_id=self.node_config.id,
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name,
                row_number=row_number,
                error=error_msg
            )
            raise
