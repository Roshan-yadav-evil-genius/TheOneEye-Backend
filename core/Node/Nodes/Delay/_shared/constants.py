"""
Delay Constants

Shared constants for delay nodes.
"""

# Conversion factors to seconds
TIME_UNIT_TO_SECONDS = {
    "seconds": 1,
    "minutes": 60,
    "hours": 3600,
    "days": 86400,
    "months": 2592000,  # 30 days approximation
}

# Unit choices for forms
UNIT_CHOICES = [
    ("seconds", "Seconds"),
    ("minutes", "Minutes"),
    ("hours", "Hours"),
    ("days", "Days"),
    ("months", "Months"),
]

