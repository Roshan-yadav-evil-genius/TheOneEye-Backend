"""
Google Sheets Get Record By Query Node

Single Responsibility: Execute row query from Google Sheets by column conditions.

This node handles:
- Form value extraction
- Jinja template rendering for query conditions
- Parsing and validating query conditions
- Calling GoogleSheetsService to query row data
- Formatting output with header mapping
"""

import json
import structlog
from typing import Optional

from jinja2 import Template

from ....Core.Node.Core import BlockingNode, NodeOutput, PoolType
from ....Core.Form.Core.BaseForm import BaseForm
from .form import GoogleSheetsGetRecordByQueryForm
from .._shared.google_sheets_service import GoogleSheetsService

logger = structlog.get_logger(__name__)


class GoogleSheetsGetRecordByQueryNode(BlockingNode):
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
        
        Args:
            previous_node_output: Output from the previous node in the workflow
            
        Returns:
            NodeOutput with google_sheets data containing the matched row values,
            headers, and mapped data dictionary
            
        Raises:
            Exception: If query fails or no match found
        """
        # Extract form values
        account_id = self.form.cleaned_data.get('google_account')
        spreadsheet_id = self.form.cleaned_data.get('spreadsheet')
        sheet_name = self.form.cleaned_data.get('sheet')
        header_row = self.form.cleaned_data.get('header_row', 1)
        query_conditions_raw = self.form.cleaned_data.get('query_conditions', '')
        
        logger.info(
            "Querying Google Sheet by conditions",
            node_id=self.node_config.id,
            spreadsheet_id=spreadsheet_id,
            sheet_name=sheet_name,
            header_row=header_row
        )
        
        try:
            # Render Jinja template in query_conditions field
            template = Template(query_conditions_raw)
            rendered_query = template.render(data=previous_node_output.data)
            
            logger.debug(
                "Rendered query conditions",
                node_id=self.node_config.id,
                raw=query_conditions_raw,
                rendered=rendered_query
            )
            
            # Parse rendered JSON
            try:
                query_conditions = json.loads(rendered_query)
            except json.JSONDecodeError as e:
                error_msg = f"Invalid JSON in query conditions after rendering: {e}"
                logger.error(
                    "Failed to parse query conditions",
                    node_id=self.node_config.id,
                    rendered_query=rendered_query,
                    error=error_msg
                )
                raise Exception(error_msg)
            
            # Validate query conditions structure
            if not isinstance(query_conditions, list):
                raise Exception("Query conditions must be a JSON array")
            
            if len(query_conditions) == 0:
                raise Exception("Query conditions array cannot be empty")
            
            # Validate each condition
            for idx, condition in enumerate(query_conditions):
                if not isinstance(condition, dict):
                    raise Exception(f"Condition at index {idx} must be an object")
                
                required_keys = ['column', 'value', 'operator', 'case_sensitive']
                for key in required_keys:
                    if key not in condition:
                        raise Exception(f"Condition at index {idx} is missing required field: {key}")
                
                # Validate operator
                operator = condition.get('operator')
                if operator not in ['equals', 'contains']:
                    raise Exception(
                        f"Condition at index {idx} has invalid operator '{operator}'. "
                        f"Must be 'equals' or 'contains'"
                    )
                
                # Validate case_sensitive is boolean
                case_sensitive = condition.get('case_sensitive')
                if not isinstance(case_sensitive, bool):
                    raise Exception(
                        f"Condition at index {idx} has invalid case_sensitive value. "
                        f"Must be true or false (boolean)"
                    )
            
            # Create service instance with the selected account
            service = GoogleSheetsService(account_id)
            
            # Query row by conditions
            row_data = await service.query_row_by_conditions(
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name,
                query_conditions=query_conditions,
                header_row=header_row
            )
            
            # Check if no match found
            if row_data is None:
                logger.info(
                    "No row found matching query conditions",
                    node_id=self.node_config.id,
                    spreadsheet_id=spreadsheet_id,
                    sheet_name=sheet_name,
                    conditions_count=len(query_conditions)
                )
                raise Exception(
                    f"No row found matching the query conditions. "
                    f"Searched {len(query_conditions)} condition(s) in sheet '{sheet_name}'"
                )
            
            logger.info(
                "Row found matching query conditions",
                node_id=self.node_config.id,
                row_number=row_data.get('row_number'),
                columns=len(row_data.get('values', [])),
                headers_count=len(row_data.get('headers', []))
            )
            
            # Attach result to output data with unique key
            output_key = self.get_unique_output_key(previous_node_output, 'google_sheets')
            previous_node_output.data[output_key] = row_data
            
            # Return NodeOutput with metadata
            return NodeOutput(
                id=previous_node_output.id,
                data=previous_node_output.data,
                metadata={
                    "sourceNodeID": self.node_config.id,
                    "sourceNodeName": self.node_config.type,
                    "operation": "get_record_by_query",
                    "spreadsheet_id": spreadsheet_id,
                    "sheet_name": sheet_name,
                    "row_number": row_data.get('row_number'),
                    "header_row": header_row,
                    "query_conditions_count": len(query_conditions)
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
                "Failed to query row by conditions",
                node_id=self.node_config.id,
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name,
                error=error_msg
            )
            raise

