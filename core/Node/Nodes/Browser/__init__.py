"""
Browser Nodes Package

Provides browser automation nodes using Playwright.
"""

from .WebPageLoader import WebPageLoader, WebPageLoaderForm
from .SendConnectionRequest import SendConnectionRequest, SendConnectionRequestForm
from .NetworkInterceptor import NetworkInterceptor, NetworkInterceptorForm

__all__ = [
    'WebPageLoader', 
    'WebPageLoaderForm', 
    'SendConnectionRequest', 
    'SendConnectionRequestForm',
    'NetworkInterceptor',
    'NetworkInterceptorForm'
]
