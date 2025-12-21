"""
Browser Nodes Package

Provides browser automation nodes using Playwright.
"""

from .WebPageLoader import WebPageLoader, WebPageLoaderForm
from .SendConnectionRequest import SendConnectionRequest, SendConnectionRequestForm

__all__ = [
    'WebPageLoader', 
    'WebPageLoaderForm', 
    'SendConnectionRequest', 
    'SendConnectionRequestForm'
]
