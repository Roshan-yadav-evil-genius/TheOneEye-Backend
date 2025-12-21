"""
Google Sheets Form Utilities

Single Responsibility: Shared form components for Google Sheets nodes.

This module provides reusable utilities:
- DynamicChoiceField: ChoiceField that skips validation for dynamic options
- get_google_account_choices(): Fetches Google accounts from backend API
- populate_spreadsheet_choices(): Shared logic for spreadsheet dropdown
- populate_sheet_choices(): Shared logic for sheet dropdown
"""

from typing import List, Tuple, Optional, Dict, Any
from django import forms
import structlog
import asyncio

logger = structlog.get_logger(__name__)


class DynamicChoiceField(forms.ChoiceField):
    """
    ChoiceField that skips choice validation for dynamically populated options.
    
    Use this for fields whose choices are loaded dynamically (e.g., from API)
    and aren't available at form instantiation time during node execution.
    """
    
    def validate(self, value):
        """Skip choice validation - only check if required."""
        if value in self.empty_values and self.required:
            raise forms.ValidationError(
                self.error_messages['required'], 
                code='required'
            )


def get_google_account_choices() -> List[Tuple[str, str]]:
    """
    Fetch available Google accounts from Django model.
    
    Returns:
        List of (id, display_text) tuples for ChoiceField
    """
    try:
        from apps.authentication.models import GoogleConnectedAccount
        
        accounts = GoogleConnectedAccount.objects.filter(is_active=True).order_by('name')
        return [("", "-- Select Account --")] + [
            (str(account.id), f"{account.name} ({account.email})") 
            for account in accounts
        ]
    except Exception as e:
        logger.warning("Failed to fetch Google accounts", error=str(e))
    
    return [("", "-- Select Account --")]


def populate_spreadsheet_choices(
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
        # Run async method from sync context
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, we need to use a different approach
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, service.list_spreadsheets())
                    spreadsheets = future.result()
            else:
                spreadsheets = loop.run_until_complete(service.list_spreadsheets())
        except RuntimeError:
            # No event loop, create one
            spreadsheets = asyncio.run(service.list_spreadsheets())
        
        logger.debug(
            "Populated spreadsheets",
            account_id=account_id,
            count=len(spreadsheets)
        )
        
        return [("", "-- Select Spreadsheet --")] + list(spreadsheets)
        
    except Exception as e:
        logger.error(
            "Failed to load spreadsheets",
            account_id=account_id,
            error=str(e)
        )
        return [("", "-- Error loading spreadsheets --")]


def populate_sheet_choices(
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
        # Run async method from sync context
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, we need to use a different approach
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, service.list_sheets(spreadsheet_id))
                    sheets = future.result()
            else:
                sheets = loop.run_until_complete(service.list_sheets(spreadsheet_id))
        except RuntimeError:
            # No event loop, create one
            sheets = asyncio.run(service.list_sheets(spreadsheet_id))
        
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
        
    except Exception as e:
        logger.error(
            "Failed to load sheets",
            spreadsheet_id=spreadsheet_id,
            error=str(e)
        )
        return [("", "-- Error loading sheets --")]

