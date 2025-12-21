"""
Google Sheets Get Row Form

Single Responsibility: Form field definitions and cascading dependencies.

This form handles:
- Google account selection (loaded from backend API)
- Spreadsheet selection (cascades from account)
- Sheet selection (cascades from spreadsheet)
- Row number input
- Header row configuration
"""

from django import forms
import structlog

from ....Core.Form.Core.BaseForm import BaseForm
from .._shared.form_utils import (
    DynamicChoiceField,
    get_google_account_choices,
    populate_spreadsheet_choices,
    populate_sheet_choices
)

logger = structlog.get_logger(__name__)


class GoogleSheetsGetRowForm(BaseForm):
    """
    Form for Google Sheets Get Row node with cascading dropdowns.
    
    Field Dependencies:
    - google_account -> spreadsheet (selecting account loads spreadsheets)
    - spreadsheet -> sheet (selecting spreadsheet loads sheets)
    
    The form uses the existing BaseForm dependency system to handle
    cascading field updates via the frontend.
    """
    
    google_account = forms.ChoiceField(
        choices=[("", "-- Select Account --")],
        required=True,
        help_text="Select a connected Google account"
    )
    
    # Use DynamicChoiceField for fields populated via cascading API calls
    spreadsheet = DynamicChoiceField(
        choices=[("", "-- Select Spreadsheet --")],
        required=True,
        help_text="Select a Google Spreadsheet"
    )
    
    sheet = DynamicChoiceField(
        choices=[("", "-- Select Sheet --")],
        required=True,
        help_text="Select a sheet within the spreadsheet"
    )
    
    row_number = forms.IntegerField(
        min_value=1,
        required=True,
        help_text="Row number to retrieve (1-indexed)"
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
    
    def get_field_dependencies(self):
        """
        Define cascading field dependencies.
        
        Returns:
            Dict mapping parent field -> list of dependent fields
        """
        return {
            'google_account': ['spreadsheet'],  # Account selection loads spreadsheets
            'spreadsheet': ['sheet']            # Spreadsheet selection loads sheets
        }
    
    def populate_field(self, field_name, parent_value, form_values=None):
        """
        Provide choices for dependent fields based on parent value.
        
        Called by the form dependency system when a parent field changes.
        
        Args:
            field_name: Name of the dependent field to populate
            parent_value: Value of the immediate parent field
            form_values: All current form values for multi-parent access
            
        Returns:
            List of (value, text) tuples for the field choices
        """
        form_values = form_values or {}
        
        if field_name == 'spreadsheet':
            return populate_spreadsheet_choices(parent_value)
        
        elif field_name == 'sheet':
            return populate_sheet_choices(
                spreadsheet_id=parent_value,
                form_values=form_values
            )
        
        return []

