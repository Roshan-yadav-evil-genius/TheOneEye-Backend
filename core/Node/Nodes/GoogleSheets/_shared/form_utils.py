"""
Google Sheets Form Utilities

Single Responsibility: Shared form components for Google Sheets nodes.

This module provides reusable utilities:
- get_google_account_choices(): Fetches Google accounts from backend API
- populate_spreadsheet_choices(): Shared logic for spreadsheet dropdown
- populate_sheet_choices(): Shared logic for sheet dropdown
"""

from typing import List, Tuple, Optional, Dict, Any
import structlog
from asgiref.sync import sync_to_async
from google.auth.exceptions import RefreshError
from apps.common.exceptions import ValidationError

logger = structlog.get_logger(__name__)


def get_google_account_choices() -> List[Tuple[str, str]]:
    """
    Fetch available Google accounts from Django model.
    
    This function is async-safe and can be called from both sync and async contexts.
    Uses sync_to_async to safely access the database from any context.
    
    Returns:
        List of (id, display_text) tuples for ChoiceField
    """
    try:
        from apps.authentication.models import GoogleConnectedAccount
        import asyncio
        import concurrent.futures
        
        # Define the database query function wrapped with sync_to_async
        @sync_to_async
        def _fetch_accounts():
            accounts = GoogleConnectedAccount.objects.filter(is_active=True).order_by('name')
            return [("", "-- Select Account --")] + [
                (str(account.id), f"{account.name} ({account.email})") 
                for account in accounts
            ]
        
        # Check if we're in an async context
        try:
            loop = asyncio.get_running_loop()
            # We're in an async context - can't use async_to_sync
            # Run in a separate thread with its own event loop
            def run_in_thread():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(_fetch_accounts())
                finally:
                    new_loop.close()
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_in_thread)
                return future.result(timeout=5)
        except RuntimeError:
            # No running event loop - we're in sync context
            # Safe to use async_to_sync
            from asgiref.sync import async_to_sync
            return async_to_sync(_fetch_accounts)()
    except Exception as e:
        logger.warning("Failed to fetch Google accounts", error=str(e))
    
    return [("", "-- Select Account --")]


async def populate_spreadsheet_choices(
    account_id: str
) -> List[Tuple[str, str]]:
    """
    Populate spreadsheet choices for a given Google account.
    
    Args:
        account_id: The Google account ID to fetch spreadsheets for
        
    Returns:
        List of (spreadsheet_id, spreadsheet_name) tuples
    """
    from .google_sheets_service import GoogleSheetsService
    
    if not account_id:
        return [("", "-- Select Spreadsheet --")]
    
    try:
        service = GoogleSheetsService(account_id)
        spreadsheets = await service.list_spreadsheets()
        
        logger.debug(
            "Populated spreadsheets",
            account_id=account_id,
            count=len(spreadsheets)
        )
        
        return [("", "-- Select Spreadsheet --")] + list(spreadsheets)
        
    except RefreshError as e:
        # Token refresh failed - account needs reconnection
        error_msg = str(e)
        logger.error(
            "Google account token expired or revoked",
            account_id=account_id,
            error=error_msg
        )
        raise ValidationError(
            "Google account token has expired or been revoked. Please reconnect your Google account.",
            detail=f"Account ID: {account_id}. Error: {error_msg}",
            extra_data={'account_id': account_id, 'error_type': 'token_expired'}
        )
    except Exception as e:
        error_msg = str(e)
        # Check for invalid_grant in error message
        if 'invalid_grant' in error_msg.lower() or 'expired' in error_msg.lower() or 'revoked' in error_msg.lower():
            logger.error(
                "Google account token expired or revoked",
                account_id=account_id,
                error=error_msg
            )
            raise ValidationError(
                "Google account token has expired or been revoked. Please reconnect your Google account.",
                detail=f"Account ID: {account_id}. Error: {error_msg}",
                extra_data={'account_id': account_id, 'error_type': 'token_expired'}
            )
        
        logger.error(
            "Failed to load spreadsheets",
            account_id=account_id,
            error=error_msg
        )
        raise ValidationError(
            "Failed to load spreadsheets from Google account.",
            detail=f"Account ID: {account_id}. Error: {error_msg}",
            extra_data={'account_id': account_id}
        )


async def populate_sheet_choices(
    spreadsheet_id: str,
    account_id: Optional[str] = None,
    form_values: Optional[Dict[str, Any]] = None
) -> List[Tuple[str, str]]:
    """
    Populate sheet choices for a given spreadsheet.
    
    Args:
        spreadsheet_id: The spreadsheet ID to fetch sheets for
        account_id: The Google account ID (optional if in form_values)
        form_values: Form values dict to extract account_id from
        
    Returns:
        List of (sheet_name, sheet_name) tuples
    """
    from .google_sheets_service import GoogleSheetsService
    
    if not spreadsheet_id:
        return [("", "-- Select Sheet --")]
    
    # Get account_id from parameter or form_values
    if not account_id and form_values:
        account_id = form_values.get('google_account')
    
    if not account_id:
        logger.warning("No account ID available for sheet loading")
        return [("", "-- Select account first --")]
    
    try:
        service = GoogleSheetsService(account_id)
        sheets = await service.list_sheets(spreadsheet_id)
        
        logger.debug(
            "Populated sheets",
            spreadsheet_id=spreadsheet_id,
            account_id=account_id,
            count=len(sheets)
        )
        
        # Return sheet_name as value (needed for Sheets API calls)
        return [("", "-- Select Sheet --")] + [
            (name, name) for sheet_id, name in sheets
        ]
        
    except RefreshError as e:
        # Token refresh failed - account needs reconnection
        error_msg = str(e)
        logger.error(
            "Google account token expired or revoked",
            spreadsheet_id=spreadsheet_id,
            account_id=account_id,
            error=error_msg
        )
        raise ValidationError(
            "Google account token has expired or been revoked. Please reconnect your Google account.",
            detail=f"Account ID: {account_id}, Spreadsheet ID: {spreadsheet_id}. Error: {error_msg}",
            extra_data={'account_id': account_id, 'spreadsheet_id': spreadsheet_id, 'error_type': 'token_expired'}
        )
    except Exception as e:
        error_msg = str(e)
        # Check for invalid_grant in error message
        if 'invalid_grant' in error_msg.lower() or 'expired' in error_msg.lower() or 'revoked' in error_msg.lower():
            logger.error(
                "Google account token expired or revoked",
                spreadsheet_id=spreadsheet_id,
                account_id=account_id,
                error=error_msg
            )
            raise ValidationError(
                "Google account token has expired or been revoked. Please reconnect your Google account.",
                detail=f"Account ID: {account_id}, Spreadsheet ID: {spreadsheet_id}. Error: {error_msg}",
                extra_data={'account_id': account_id, 'spreadsheet_id': spreadsheet_id, 'error_type': 'token_expired'}
            )
        
        logger.error(
            "Failed to load sheets",
            spreadsheet_id=spreadsheet_id,
            error=error_msg
        )
        raise ValidationError(
            "Failed to load sheets from Google Spreadsheet.",
            detail=f"Account ID: {account_id}, Spreadsheet ID: {spreadsheet_id}. Error: {error_msg}",
            extra_data={'account_id': account_id, 'spreadsheet_id': spreadsheet_id}
        )

