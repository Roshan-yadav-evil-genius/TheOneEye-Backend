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

from ....Core.Form import BaseForm
from ....Core.Form.Fields import DependentChoiceField
from .._shared.form_utils import (
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
