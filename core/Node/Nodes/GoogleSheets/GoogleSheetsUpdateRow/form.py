"""
Google Sheets Update Row Form

Single Responsibility: Form field definitions and cascading dependencies.

This form handles:
- Google account selection (loaded from backend API)
- Spreadsheet selection (cascades from account)
- Sheet selection (cascades from spreadsheet)
- Row number input
- Row data input (JSON format for header-value mapping)
- Header row configuration
"""

import json
from django import forms
import structlog

from ....Core.Form import BaseForm
from ....Core.Form.Fields import DependentChoiceField, JSONTextareaWidget
from .._shared.form_utils import (
    get_google_account_choices,
    populate_spreadsheet_choices,
    populate_sheet_choices
)

logger = structlog.get_logger(__name__)


class GoogleSheetsUpdateRowForm(BaseForm):
    """
    Form for Google Sheets Update Row node with cascading dropdowns.
    
    Field Dependencies:
    - google_account -> spreadsheet (selecting account loads spreadsheets)
    - spreadsheet -> sheet (selecting spreadsheet loads sheets)
    """
    
    google_account = forms.ChoiceField(
        choices=[("", "-- Select Account --")],
        required=True,
        help_text="Select a connected Google account"
    )
    
    spreadsheet = DependentChoiceField(
        choices=[("", "-- Select Spreadsheet --")],
        required=True,
        help_text="Select a Google Spreadsheet",
        dependent_on=["google_account"]
    )
    
    sheet = DependentChoiceField(
        choices=[("", "-- Select Sheet --")],
        required=True,
        help_text="Select a sheet within the spreadsheet",
        dependent_on=["google_account", "spreadsheet"]
    )
    
    row_number = forms.IntegerField(
        min_value=1,
        required=True,
        help_text="Row number to update (1-indexed)"
    )
    
    row_data = forms.CharField(
        widget=JSONTextareaWidget(attrs={'rows': 5}),
        required=True,
        help_text='JSON object mapping column headers to values, e.g. {"Name": "John", "Email": "john@example.com"}'
    )
    
    header_row = forms.IntegerField(
        min_value=1,
        initial=1,
        required=True,
        help_text="Row containing column headers (default: 1)"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Dynamically populate Google account choices from backend API
        self.fields['google_account'].choices = get_google_account_choices()
    
    def spreadsheet_loader(self):
        """
        Load spreadsheet choices based on selected Google account.
        Called by the form dependency system when google_account changes.
        """
        account_id = self._field_values.get('google_account')
        if not account_id:
            return [("", "-- Select Spreadsheet --")]
        
        return populate_spreadsheet_choices(account_id)
    
    def sheet_loader(self):
        """
        Load sheet choices based on selected spreadsheet.
        Called by the form dependency system when spreadsheet changes.
        """
        spreadsheet_id = self._field_values.get('spreadsheet')
        account_id = self._field_values.get('google_account')
        
        if not spreadsheet_id or not account_id:
            return [("", "-- Select Sheet --")]
        
        form_values = {'google_account': account_id}
        return populate_sheet_choices(
            spreadsheet_id=spreadsheet_id,
            form_values=form_values
        )
    
    def clean_row_data(self):
        """
        Validate that row_data is valid JSON and is a dictionary.
        
        Returns:
            dict: Parsed JSON data as a dictionary
            
        Raises:
            ValidationError: If JSON is invalid or not a dictionary
        """
        row_data = self.cleaned_data.get('row_data', '')
        
        try:
            parsed = json.loads(row_data)
            if not isinstance(parsed, dict):
                raise forms.ValidationError(
                    "Row data must be a JSON object (dictionary), not a list or primitive"
                )
            return parsed
        except json.JSONDecodeError as e:
            raise forms.ValidationError(f"Invalid JSON: {e}")
