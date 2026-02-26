"""
Google Sheets Service

Single Responsibility: Google Sheets API operations using official Google client.

This service handles all interactions with Google Sheets and Drive APIs:
- Fetch list of spreadsheets from Google Drive
- Fetch sheets within a spreadsheet
- Read row data from a sheet (with optional header mapping)
"""

from typing import List, Tuple, Dict, Any, Optional
import structlog
from asgiref.sync import sync_to_async

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError

logger = structlog.get_logger(__name__)


class GoogleSheetsService:
    """
    Service to interact with Google Sheets API using official Google client.
    
    Single Responsibility: Google Sheets/Drive API operations only.
    Does NOT handle:
    - Form field logic (handled by Form)
    - Node execution logic (handled by Node)
    """
    
    def __init__(self, account_id: str):
        """
        Initialize with a GoogleConnectedAccount ID.
        
        Args:
            account_id: UUID of the GoogleConnectedAccount
        """
        self.account_id = account_id
        self._credentials: Optional[Credentials] = None
        self._sheets_service = None
        self._drive_service = None
    
    async def _get_credentials(self) -> Credentials:
        """
        Build Google credentials from stored OAuth tokens.
        Fetches from Django model directly using async-safe calls.
        
        Returns:
            Credentials: Google OAuth2 credentials object
            
        Raises:
            Exception: If credentials cannot be fetched
        """
        if self._credentials and self._credentials.valid:
            return self._credentials
        
        # Fetch account from Django model using sync_to_async
        from apps.authentication.models import GoogleConnectedAccount
        import asyncio
        import concurrent.futures
        
        def _fetch_account_sync():
            try:
                return GoogleConnectedAccount.objects.get(id=self.account_id, is_active=True)
            except GoogleConnectedAccount.DoesNotExist:
                logger.error(
                    "Google account not found or inactive",
                    account_id=self.account_id
                )
                raise Exception(f"Google account not found or inactive: {self.account_id}")
        
        # Use safe async wrapper that handles CurrentThreadExecutor issue
        async def _fetch_account_async():
            try:
                loop = asyncio.get_running_loop()
                # We're in async context - use thread pool executor to avoid CurrentThreadExecutor
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    return await loop.run_in_executor(executor, _fetch_account_sync)
            except RuntimeError:
                # No running loop - safe to use sync_to_async
                return await sync_to_async(_fetch_account_sync)()
        
        account = await _fetch_account_async()
        
        # Proactively refresh token if needed using OAuth service
        def _refresh_token_if_needed_sync():
            from apps.authentication.services.google_oauth_service import GoogleOAuthService
            oauth_service = GoogleOAuthService()
            try:
                # This will refresh if expired, or return existing if valid
                access_token, was_refreshed = oauth_service.get_valid_credentials(account)
                # Reload account to get updated token
                account.refresh_from_db()
                return account
            except Exception as e:
                error_msg = str(e)
                if 'invalid_grant' in error_msg.lower() or 'expired' in error_msg.lower() or 'revoked' in error_msg.lower():
                    logger.error(
                        "Google account token expired or revoked - reconnection required",
                        account_id=self.account_id,
                        error=error_msg
                    )
                    raise Exception(
                        f"Google account token has expired or been revoked. "
                        f"Please reconnect your Google account (ID: {self.account_id}). "
                        f"Error: {error_msg}"
                    )
                raise
        
        async def _refresh_token_if_needed_async():
            try:
                loop = asyncio.get_running_loop()
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    return await loop.run_in_executor(executor, _refresh_token_if_needed_sync)
            except RuntimeError:
                return await sync_to_async(_refresh_token_if_needed_sync)()
        
        # Refresh token proactively
        account = await _refresh_token_if_needed_async()
        
        # Get client_id and client_secret from Django settings for token refresh
        def _get_oauth_config_sync():
            from django.conf import settings
            return {
                'client_id': getattr(settings, 'GOOGLE_CLIENT_ID', ''),
                'client_secret': getattr(settings, 'GOOGLE_CLIENT_SECRET', ''),
            }
        
        async def _get_oauth_config_async():
            try:
                loop = asyncio.get_running_loop()
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    return await loop.run_in_executor(executor, _get_oauth_config_sync)
            except RuntimeError:
                return await sync_to_async(_get_oauth_config_sync)()
        
        # Convert scope keys to scope URLs
        def _convert_scopes_sync():
            from apps.authentication.services.google_oauth_service import GoogleOAuthService
            oauth_service = GoogleOAuthService()
            # account.scopes contains scope keys like ['sheets', 'drive_readonly']
            # Convert them to full URLs
            scope_keys = account.scopes or []
            return oauth_service.get_scope_urls(scope_keys)
        
        async def _convert_scopes_async():
            try:
                loop = asyncio.get_running_loop()
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    return await loop.run_in_executor(executor, _convert_scopes_sync)
            except RuntimeError:
                return await sync_to_async(_convert_scopes_sync)()
        
        oauth_config = await _get_oauth_config_async()
        scope_urls = await _convert_scopes_async()
        
        # Build Credentials object for Google API client
        self._credentials = Credentials(
            token=account.access_token,
            refresh_token=account.refresh_token,
            token_uri='https://oauth2.googleapis.com/token',
            client_id=oauth_config['client_id'],
            client_secret=oauth_config['client_secret'],
            scopes=scope_urls
        )
        
        logger.debug(
            "Credentials loaded",
            account_id=self.account_id,
            has_refresh_token=bool(account.refresh_token)
        )
        
        return self._credentials
    
    async def _get_sheets_service(self):
        """
        Get or create Google Sheets API service.
        
        Returns:
            Resource: Google Sheets API service instance
        """
        if self._sheets_service is None:
            credentials = await self._get_credentials()
            self._sheets_service = build('sheets', 'v4', credentials=credentials)
        return self._sheets_service
    
    async def _get_drive_service(self):
        """
        Get or create Google Drive API service.
        
        Returns:
            Resource: Google Drive API service instance
        """
        if self._drive_service is None:
            credentials = await self._get_credentials()
            self._drive_service = build('drive', 'v3', credentials=credentials)
        return self._drive_service
    
    async def list_spreadsheets(self) -> List[Tuple[str, str]]:
        """
        List all spreadsheets in user's Drive.
        
        Uses Drive API to find all files with spreadsheet MIME type.
        
        Returns:
            List of (spreadsheet_id, name) tuples, sorted by modification time
            
        Raises:
            Exception: If token is expired/revoked with actionable error message
        """
        try:
            drive = await self._get_drive_service()
            
            results = drive.files().list(
                q="mimeType='application/vnd.google-apps.spreadsheet'",
                fields="files(id, name)",
                orderBy="modifiedTime desc",
                pageSize=100
            ).execute()
            
            files = results.get('files', [])
            
            logger.info(
                "Listed spreadsheets",
                account_id=self.account_id,
                count=len(files)
            )
            
            return [(f['id'], f['name']) for f in files]
            
        except RefreshError as e:
            error_msg = str(e)
            logger.error(
                "Token refresh failed when listing spreadsheets",
                account_id=self.account_id,
                error=error_msg
            )
            raise Exception(
                f"Google account token has expired or been revoked. "
                f"Please reconnect your Google account. Error: {error_msg}"
            )
        except HttpError as e:
            error_msg = str(e)
            # Check for invalid_grant in error details
            if 'invalid_grant' in error_msg.lower() or 'expired' in error_msg.lower() or 'revoked' in error_msg.lower():
                logger.error(
                    "Token expired/revoked when listing spreadsheets",
                    account_id=self.account_id,
                    error=error_msg
                )
                raise Exception(
                    f"Google account token has expired or been revoked. "
                    f"Please reconnect your Google account. Error: {error_msg}"
                )
            
            logger.error(
                "Failed to list spreadsheets",
                account_id=self.account_id,
                error=error_msg
            )
            raise Exception(f"Failed to list spreadsheets: {error_msg}")
    
    async def list_sheets(self, spreadsheet_id: str) -> List[Tuple[str, str]]:
        """
        List all sheets within a spreadsheet.
        
        Args:
            spreadsheet_id: The Google Spreadsheet ID
            
        Returns:
            List of (sheet_id, sheet_title) tuples
            
        Raises:
            Exception: If token is expired/revoked with actionable error message
        """
        try:
            sheets = await self._get_sheets_service()
            
            spreadsheet = sheets.spreadsheets().get(
                spreadsheetId=spreadsheet_id,
                fields="sheets.properties"
            ).execute()
            
            sheet_list = spreadsheet.get('sheets', [])
            
            logger.info(
                "Listed sheets",
                spreadsheet_id=spreadsheet_id,
                count=len(sheet_list)
            )
            
            return [
                (str(s['properties']['sheetId']), s['properties']['title'])
                for s in sheet_list
            ]
            
        except RefreshError as e:
            error_msg = str(e)
            logger.error(
                "Token refresh failed when listing sheets",
                spreadsheet_id=spreadsheet_id,
                account_id=self.account_id,
                error=error_msg
            )
            raise Exception(
                f"Google account token has expired or been revoked. "
                f"Please reconnect your Google account. Error: {error_msg}"
            )
        except HttpError as e:
            error_msg = str(e)
            # Check for invalid_grant in error details
            if 'invalid_grant' in error_msg.lower() or 'expired' in error_msg.lower() or 'revoked' in error_msg.lower():
                logger.error(
                    "Token expired/revoked when listing sheets",
                    spreadsheet_id=spreadsheet_id,
                    account_id=self.account_id,
                    error=error_msg
                )
                raise Exception(
                    f"Google account token has expired or been revoked. "
                    f"Please reconnect your Google account. Error: {error_msg}"
                )
            
            logger.error(
                "Failed to list sheets",
                spreadsheet_id=spreadsheet_id,
                error=error_msg
            )
            raise Exception(f"Failed to list sheets: {error_msg}")
    
    async def get_row(self, spreadsheet_id: str, sheet_name: str, row_number: int) -> Dict[str, Any]:
        """
        Get data from a specific row (values only).
        
        Args:
            spreadsheet_id: The Google Spreadsheet ID
            sheet_name: Name of the sheet tab
            row_number: Row number (1-indexed)
            
        Returns:
            Dict with row data:
            {
                "row_number": 5,
                "values": ["John", "Doe", "john@example.com"],
                "spreadsheet_id": "...",
                "sheet_name": "Sheet1"
            }
            
        Raises:
            Exception: If row cannot be fetched
        """
        try:
            sheets = await self._get_sheets_service()
            
            # A1 notation for the entire row
            range_notation = f"'{sheet_name}'!{row_number}:{row_number}"
            
            result = sheets.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_notation
            ).execute()
            
            values = result.get('values', [[]])[0] if result.get('values') else []
            
            logger.info(
                "Row retrieved",
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name,
                row_number=row_number,
                columns=len(values)
            )
            
            return {
                "row_number": row_number,
                "values": values,
                "range": result.get('range'),
                "spreadsheet_id": spreadsheet_id,
                "sheet_name": sheet_name
            }
            
        except RefreshError as e:
            error_msg = str(e)
            logger.error(
                "Token refresh failed when getting row",
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name,
                row_number=row_number,
                account_id=self.account_id,
                error=error_msg
            )
            raise Exception(
                f"Google account token has expired or been revoked. "
                f"Please reconnect your Google account. Error: {error_msg}"
            )
        except HttpError as e:
            error_msg = str(e)
            # Check for invalid_grant in error details
            if 'invalid_grant' in error_msg.lower() or 'expired' in error_msg.lower() or 'revoked' in error_msg.lower():
                logger.error(
                    "Token expired/revoked when getting row",
                    spreadsheet_id=spreadsheet_id,
                    sheet_name=sheet_name,
                    row_number=row_number,
                    account_id=self.account_id,
                    error=error_msg
                )
                raise Exception(
                    f"Google account token has expired or been revoked. "
                    f"Please reconnect your Google account. Error: {error_msg}"
                )
            
            logger.error(
                "Failed to get row",
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name,
                row_number=row_number,
                error=error_msg
            )
            raise Exception(f"Failed to get row: {error_msg}")
    
    async def get_row_with_headers(
        self, 
        spreadsheet_id: str, 
        sheet_name: str, 
        row_number: int,
        header_row: int = 1
    ) -> Dict[str, Any]:
        """
        Get row data with column headers as keys.
        
        Fetches both the header row and the target row in a single batch request,
        then maps the values to their corresponding headers.
        
        Args:
            spreadsheet_id: The Google Spreadsheet ID
            sheet_name: Name of the sheet tab
            row_number: Row number to retrieve (1-indexed)
            header_row: Row containing column headers (default: 1)
            
        Returns:
            Dict with row data including key-value pairs based on headers:
            {
                "row_number": 5,
                "values": ["John", "Doe", "john@example.com"],
                "headers": ["First Name", "Last Name", "Email"],
                "data": {
                    "First Name": "John",
                    "Last Name": "Doe",
                    "Email": "john@example.com"
                },
                "spreadsheet_id": "...",
                "sheet_name": "Sheet1"
            }
            
        Raises:
            Exception: If row cannot be fetched
        """
        try:
            sheets = await self._get_sheets_service()
            
            # Fetch both header row and data row in one batch request
            ranges = [
                f"'{sheet_name}'!{header_row}:{header_row}",
                f"'{sheet_name}'!{row_number}:{row_number}"
            ]
            
            result = sheets.spreadsheets().values().batchGet(
                spreadsheetId=spreadsheet_id,
                ranges=ranges
            ).execute()
            
            value_ranges = result.get('valueRanges', [])
            
            # Extract headers and values
            headers = value_ranges[0].get('values', [[]])[0] if len(value_ranges) > 0 and value_ranges[0].get('values') else []
            values = value_ranges[1].get('values', [[]])[0] if len(value_ranges) > 1 and value_ranges[1].get('values') else []
            
            # Create key-value mapping (header -> value)
            row_dict = {}
            for i, header in enumerate(headers):
                row_dict[header] = values[i] if i < len(values) else ""
            
            logger.info(
                "Row with headers retrieved",
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name,
                row_number=row_number,
                header_row=header_row,
                columns=len(values),
                headers_count=len(headers)
            )
            
            return {
                "row_number": row_number,
                "header_row": header_row,
                "values": values,
                "headers": headers,
                "data": row_dict,
                "spreadsheet_id": spreadsheet_id,
                "sheet_name": sheet_name
            }
            
        except RefreshError as e:
            error_msg = str(e)
            logger.error(
                "Token refresh failed when getting row with headers",
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name,
                row_number=row_number,
                account_id=self.account_id,
                error=error_msg
            )
            raise Exception(
                f"Google account token has expired or been revoked. "
                f"Please reconnect your Google account. Error: {error_msg}"
            )
        except HttpError as e:
            error_msg = str(e)
            # Check for invalid_grant in error details
            if 'invalid_grant' in error_msg.lower() or 'expired' in error_msg.lower() or 'revoked' in error_msg.lower():
                logger.error(
                    "Token expired/revoked when getting row with headers",
                    spreadsheet_id=spreadsheet_id,
                    sheet_name=sheet_name,
                    row_number=row_number,
                    account_id=self.account_id,
                    error=error_msg
                )
                raise Exception(
                    f"Google account token has expired or been revoked. "
                    f"Please reconnect your Google account. Error: {error_msg}"
                )
            
            logger.error(
                "Failed to get row with headers",
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name,
                row_number=row_number,
                error=error_msg
            )
            raise Exception(f"Failed to get row: {error_msg}")
    
    async def update_row(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        row_number: int,
        values: List[Any],
        start_column: str = "A"
    ) -> Dict[str, Any]:
        """
        Update data in a specific row.
        
        Args:
            spreadsheet_id: The Google Spreadsheet ID
            sheet_name: Name of the sheet tab
            row_number: Row number to update (1-indexed)
            values: List of values to write to the row
            start_column: Column letter to start writing from (default: A)
            
        Returns:
            Dict with update result:
            {
                "row_number": 5,
                "updated_cells": 3,
                "updated_range": "Sheet1!A5:C5",
                "spreadsheet_id": "...",
                "sheet_name": "Sheet1"
            }
            
        Raises:
            Exception: If row cannot be updated
        """
        try:
            sheets = await self._get_sheets_service()
            
            # Calculate end column based on number of values
            end_column_index = ord(start_column.upper()) - ord('A') + len(values)
            end_column = chr(ord('A') + end_column_index - 1)
            
            # A1 notation for the range to update
            range_notation = f"'{sheet_name}'!{start_column}{row_number}:{end_column}{row_number}"
            
            body = {
                'values': [values]  # Single row as 2D array
            }
            
            result = sheets.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_notation,
                valueInputOption='USER_ENTERED',  # Parse values like user input
                body=body
            ).execute()
            
            logger.info(
                "Row updated",
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name,
                row_number=row_number,
                updated_cells=result.get('updatedCells', 0)
            )
            
            return {
                "row_number": row_number,
                "updated_cells": result.get('updatedCells', 0),
                "updated_range": result.get('updatedRange'),
                "spreadsheet_id": spreadsheet_id,
                "sheet_name": sheet_name
            }
            
        except RefreshError as e:
            error_msg = str(e)
            logger.error(
                "Token refresh failed when updating row",
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name,
                row_number=row_number,
                account_id=self.account_id,
                error=error_msg
            )
            raise Exception(
                f"Google account token has expired or been revoked. "
                f"Please reconnect your Google account. Error: {error_msg}"
            )
        except HttpError as e:
            error_msg = str(e)
            # Check for invalid_grant in error details
            if 'invalid_grant' in error_msg.lower() or 'expired' in error_msg.lower() or 'revoked' in error_msg.lower():
                logger.error(
                    "Token expired/revoked when updating row",
                    spreadsheet_id=spreadsheet_id,
                    sheet_name=sheet_name,
                    row_number=row_number,
                    account_id=self.account_id,
                    error=error_msg
                )
                raise Exception(
                    f"Google account token has expired or been revoked. "
                    f"Please reconnect your Google account. Error: {error_msg}"
                )
            
            logger.error(
                "Failed to update row",
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name,
                row_number=row_number,
                error=error_msg
            )
            raise Exception(f"Failed to update row: {error_msg}")
    
    async def update_row_by_headers(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        row_number: int,
        data: Dict[str, Any],
        header_row: int = 1
    ) -> Dict[str, Any]:
        """
        Update row data using header names as keys.
        
        Only updates columns specified in the data dict. Preserves existing
        values for columns not included in the data.
        
        Args:
            spreadsheet_id: The Google Spreadsheet ID
            sheet_name: Name of the sheet tab
            row_number: Row number to update (1-indexed)
            data: Dict mapping header names to values
            header_row: Row containing column headers (default: 1)
            
        Returns:
            Dict with update result including matched headers
            
        Raises:
            Exception: If row cannot be updated
        """
        try:
            sheets = await self._get_sheets_service()
            
            # Fetch BOTH header row AND current row data to preserve unmatched columns
            ranges = [
                f"'{sheet_name}'!{header_row}:{header_row}",
                f"'{sheet_name}'!{row_number}:{row_number}"
            ]
            
            batch_result = sheets.spreadsheets().values().batchGet(
                spreadsheetId=spreadsheet_id,
                ranges=ranges
            ).execute()
            
            value_ranges = batch_result.get('valueRanges', [])
            headers = value_ranges[0].get('values', [[]])[0] if len(value_ranges) > 0 and value_ranges[0].get('values') else []
            current_values = value_ranges[1].get('values', [[]])[0] if len(value_ranges) > 1 and value_ranges[1].get('values') else []
            
            if not headers:
                raise Exception("No headers found in the specified header row")
            
            # Build the row values: use new value if provided, otherwise preserve existing
            values = []
            matched_headers = []
            for i, header in enumerate(headers):
                if header in data:
                    values.append(data[header])
                    matched_headers.append(header)
                else:
                    # Preserve existing value instead of overwriting with empty
                    existing_value = current_values[i] if i < len(current_values) else ""
                    values.append(existing_value)
            
            # Update the row
            range_notation = f"'{sheet_name}'!A{row_number}"
            
            body = {
                'values': [values]
            }
            
            result = sheets.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_notation,
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
            
            logger.info(
                "Row updated by headers",
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name,
                row_number=row_number,
                matched_headers=matched_headers,
                updated_cells=result.get('updatedCells', 0)
            )
            
            return {
                "row_number": row_number,
                "updated_cells": result.get('updatedCells', 0),
                "updated_range": result.get('updatedRange'),
                "headers": headers,
                "matched_headers": matched_headers,
                "spreadsheet_id": spreadsheet_id,
                "sheet_name": sheet_name
            }
            
        except RefreshError as e:
            error_msg = str(e)
            logger.error(
                "Token refresh failed when updating row by headers",
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name,
                row_number=row_number,
                account_id=self.account_id,
                error=error_msg
            )
            raise Exception(
                f"Google account token has expired or been revoked. "
                f"Please reconnect your Google account. Error: {error_msg}"
            )
        except HttpError as e:
            error_msg = str(e)
            # Check for invalid_grant in error details
            if 'invalid_grant' in error_msg.lower() or 'expired' in error_msg.lower() or 'revoked' in error_msg.lower():
                logger.error(
                    "Token expired/revoked when updating row by headers",
                    spreadsheet_id=spreadsheet_id,
                    sheet_name=sheet_name,
                    row_number=row_number,
                    account_id=self.account_id,
                    error=error_msg
                )
                raise Exception(
                    f"Google account token has expired or been revoked. "
                    f"Please reconnect your Google account. Error: {error_msg}"
                )
            
            logger.error(
                "Failed to update row by headers",
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name,
                row_number=row_number,
                error=error_msg
            )
            raise Exception(f"Failed to update row: {error_msg}")
    
    async def query_row_by_conditions(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        query_conditions: List[Dict[str, Any]],
        header_row: int = 1,
        max_rows: int = 1000
    ) -> Optional[Dict[str, Any]]:
        """
        Query a sheet by column conditions and return the first matching row.
        
        Args:
            spreadsheet_id: The Google Spreadsheet ID
            sheet_name: Name of the sheet tab
            query_conditions: List of condition dicts with keys:
                - column: Column header name
                - value: Value to match (string for equals/contains; array for in)
                - operator: "equals", "contains", or "in"
                - case_sensitive: Boolean
            header_row: Row containing column headers (default: 1)
            max_rows: Maximum number of rows to search (default: 1000)
            
        Returns:
            Dict with matched row data (same format as get_row_with_headers) or None if no match
            
        Raises:
            Exception: If query fails or token is expired/revoked
        """
        try:
            sheets = await self._get_sheets_service()
            
            # Fetch header row
            header_range = f"'{sheet_name}'!{header_row}:{header_row}"
            header_result = sheets.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=header_range
            ).execute()
            
            headers = header_result.get('values', [[]])[0] if header_result.get('values') else []
            
            if not headers:
                raise Exception("No headers found in the specified header row")
            
            # Create column index map for quick lookup
            column_index_map = {header: idx for idx, header in enumerate(headers)}
            
            # Validate that all query columns exist
            for condition in query_conditions:
                column = condition.get('column')
                if column not in column_index_map:
                    raise Exception(f"Column '{column}' not found in sheet headers")
            
            # Fetch data rows (from header_row+1 to header_row+1+max_rows)
            start_row = header_row + 1
            end_row = start_row + max_rows
            data_range = f"'{sheet_name}'!{start_row}:{end_row}"
            
            data_result = sheets.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=data_range
            ).execute()
            
            rows = data_result.get('values', [])
            
            # Iterate through rows and check conditions
            for row_idx, row_values in enumerate(rows):
                actual_row_number = start_row + row_idx
                
                # Check if all conditions match
                all_match = True
                
                for condition in query_conditions:
                    column = condition.get('column')
                    raw_value = condition.get('value', '')
                    operator = condition.get('operator', 'equals')
                    case_sensitive = condition.get('case_sensitive', False)
                    
                    # Get column index
                    col_idx = column_index_map[column]
                    
                    # Get cell value (empty string if column doesn't exist in row)
                    cell_value = str(row_values[col_idx]) if col_idx < len(row_values) else ""
                    
                    # Apply case sensitivity to cell value
                    if not case_sensitive:
                        cell_value = cell_value.lower()
                    
                    # Check condition based on operator
                    if operator == 'equals':
                        query_value = str(raw_value)
                        if not case_sensitive:
                            query_value = query_value.lower()
                        if cell_value != query_value:
                            all_match = False
                            break
                    elif operator == 'contains':
                        query_value = str(raw_value)
                        if not case_sensitive:
                            query_value = query_value.lower()
                        if query_value not in cell_value:
                            all_match = False
                            break
                    elif operator == 'in':
                        if not isinstance(raw_value, list):
                            raise Exception(
                                "Operator 'in' requires value to be a JSON array. "
                                "Use 'equals' or 'contains' for single values."
                            )
                        allowed = [str(v).lower() if not case_sensitive else str(v) for v in raw_value]
                        if cell_value not in allowed:
                            all_match = False
                            break
                    else:
                        raise Exception(
                            f"Unsupported operator: {operator}. Use 'equals', 'contains', or 'in'"
                        )
                
                # If all conditions match, return this row
                if all_match:
                    # Pad row values to match header count
                    padded_values = row_values + [""] * (len(headers) - len(row_values))
                    
                    # Create key-value mapping (header -> value)
                    row_dict = {}
                    for i, header in enumerate(headers):
                        row_dict[header] = padded_values[i] if i < len(padded_values) else ""
                    
                    logger.info(
                        "Row found matching query conditions",
                        spreadsheet_id=spreadsheet_id,
                        sheet_name=sheet_name,
                        row_number=actual_row_number,
                        header_row=header_row,
                        conditions_count=len(query_conditions)
                    )
                    
                    return {
                        "row_number": actual_row_number,
                        "header_row": header_row,
                        "values": padded_values,
                        "headers": headers,
                        "data": row_dict,
                        "spreadsheet_id": spreadsheet_id,
                        "sheet_name": sheet_name
                    }
            
            # No match found
            logger.info(
                "No row found matching query conditions",
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name,
                conditions_count=len(query_conditions)
            )
            return None
            
        except RefreshError as e:
            error_msg = str(e)
            logger.error(
                "Token refresh failed when querying row by conditions",
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name,
                account_id=self.account_id,
                error=error_msg
            )
            raise Exception(
                f"Google account token has expired or been revoked. "
                f"Please reconnect your Google account. Error: {error_msg}"
            )
        except HttpError as e:
            error_msg = str(e)
            # Check for invalid_grant in error details
            if 'invalid_grant' in error_msg.lower() or 'expired' in error_msg.lower() or 'revoked' in error_msg.lower():
                logger.error(
                    "Token expired/revoked when querying row by conditions",
                    spreadsheet_id=spreadsheet_id,
                    sheet_name=sheet_name,
                    account_id=self.account_id,
                    error=error_msg
                )
                raise Exception(
                    f"Google account token has expired or been revoked. "
                    f"Please reconnect your Google account. Error: {error_msg}"
                )
            
            logger.error(
                "Failed to query row by conditions",
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name,
                error=error_msg
            )
            raise Exception(f"Failed to query row: {error_msg}")

