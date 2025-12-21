"""Button mapping utilities."""
from typing import Dict


class ButtonMapper:
    """Maps JavaScript button names to Playwright button names."""
    
    _BUTTON_MAP: Dict[str, str] = {
        'left': 'left',
        'right': 'right',
        'middle': 'middle'
    }
    
    @classmethod
    def map_button(cls, button: str) -> str:
        """
        Map button name to Playwright button name.
        
        Args:
            button: Button name ('left', 'right', 'middle')
            
        Returns:
            Playwright button name
        """
        return cls._BUTTON_MAP.get(button.lower(), 'left')

