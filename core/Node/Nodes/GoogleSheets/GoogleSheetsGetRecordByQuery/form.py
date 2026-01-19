"""
Google Sheets Get Record By Query Form

Single Responsibility: Form field definitions and cascading dependencies.

This form handles:
- Google account selection (loaded from backend API)
- Spreadsheet selection (cascades from account)
- Sheet selection (cascades from spreadsheet)
- Query conditions input (Jinja template that evaluates to JSON array)
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


class GoogleSheetsGetRecordByQueryForm(BaseForm):
    """
    Form for Google Sheets Get Record By Query node with cascading dropdowns.
    
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
    
    header_row = forms.IntegerField(
        min_value=1,
        initial=1,
        required=True,
        help_text="Row containing column headers (default: 1)"
    )
    
    query_conditions = forms.CharField(
        widget=JSONTextareaWidget(attrs={'rows': 10}),
        required=True,
        help_text='JSON array of query conditions with Jinja templates. Example: [{"column": "Email", "value": "{{ data.email }}", "operator": "equals", "case_sensitive": false}]'
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
    
    def clean_query_conditions(self):
        """
        Validate that query_conditions is valid JSON array with proper structure.
        
        Note: Jinja template rendering happens in the node's execute() method,
        not during form validation. This method only validates the structure
        if it's already rendered JSON.
        
        Returns:
            str: The query_conditions string (validation happens in node)
            
        Raises:
            ValidationError: If JSON structure is invalid
        """
        query_conditions = self.cleaned_data.get('query_conditions', '')
        
        # If it contains Jinja syntax, skip validation (will be validated after rendering)
        if '{{' in query_conditions or '}}' in query_conditions:
            return query_conditions
        
        # Otherwise, validate JSON structure
        try:
            parsed = json.loads(query_conditions)
            if not isinstance(parsed, list):
                raise forms.ValidationError(
                    "Query conditions must be a JSON array, not an object or primitive"
                )
            
            # Validate each condition has required fields
            for idx, condition in enumerate(parsed):
                if not isinstance(condition, dict):
                    raise forms.ValidationError(
                        f"Condition at index {idx} must be an object"
                    )
                
                required_keys = ['column', 'value', 'operator', 'case_sensitive']
                for key in required_keys:
                    if key not in condition:
                        raise forms.ValidationError(
                            f"Condition at index {idx} is missing required field: {key}"
                        )
                
                # Validate operator
                operator = condition.get('operator')
                if operator not in ['equals', 'contains']:
                    raise forms.ValidationError(
                        f"Condition at index {idx} has invalid operator '{operator}'. "
                        f"Must be 'equals' or 'contains'"
                    )
                
                # Validate case_sensitive is boolean
                case_sensitive = condition.get('case_sensitive')
                if not isinstance(case_sensitive, bool):
                    raise forms.ValidationError(
                        f"Condition at index {idx} has invalid case_sensitive value. "
                        f"Must be true or false (boolean)"
                    )
            
            return query_conditions
            
        except json.JSONDecodeError as e:
            raise forms.ValidationError(f"Invalid JSON: {e}")
