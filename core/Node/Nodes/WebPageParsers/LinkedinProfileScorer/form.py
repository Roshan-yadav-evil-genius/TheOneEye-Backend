"""
LinkedinProfileScorer Form

Single Responsibility: Form field definitions for the LinkedinProfileScorer node.
Provides fields for intent and HTML content from multiple LinkedIn pages.
"""

from django.forms import CharField
from django.forms.widgets import Textarea

from ....Core.Form import BaseForm


class LinkedinProfileScorerForm(BaseForm):
    """
    Form for configuring the LinkedinProfileScorer node.
    
    Users provide:
    - Intent: Free-form text describing what they're looking for
    - HTML content from 4 different LinkedIn pages (profile, comments, posts, reactions)
    """
    
    intent = CharField(
        widget=Textarea(attrs={'rows': 5, 'placeholder': 'Enter your intent (e.g., "I need decision-makers who are actively evaluating CRM tools")'}),
        required=True,
        help_text="Free-form description of what you're looking for in the profile."
    )
    
    profile_page_content = CharField(
        widget=Textarea(attrs={'rows': 10}),
        required=True,
        help_text="HTML content from the LinkedIn profile page."
    )
    
    comment_page_content = CharField(
        widget=Textarea(attrs={'rows': 10}),
        required=True,
        help_text="HTML content from the LinkedIn comments page."
    )
    
    posts_page_content = CharField(
        widget=Textarea(attrs={'rows': 10}),
        required=True,
        help_text="HTML content from the LinkedIn posts page."
    )
    
    recent_reactions_content = CharField(
        widget=Textarea(attrs={'rows': 10}),
        required=True,
        help_text="HTML content from the LinkedIn recent reactions page."
    )
