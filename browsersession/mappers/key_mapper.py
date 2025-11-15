"""Key mapping utilities."""
from typing import Dict, Optional


class KeyMapper:
    """Maps JavaScript key names/codes to Playwright key names."""
    
    _KEY_MAP: Dict[str, str] = {
        # Special keys
        'Enter': 'Enter',
        'Escape': 'Escape',
        'Tab': 'Tab',
        'Backspace': 'Backspace',
        'Delete': 'Delete',
        'Insert': 'Insert',
        'Home': 'Home',
        'End': 'End',
        'PageUp': 'PageUp',
        'PageDown': 'PageDown',
        'PrintScreen': 'PrintScreen',
        'Pause': 'Pause',
        'ScrollLock': 'ScrollLock',
        'NumLock': 'NumLock',
        'CapsLock': 'CapsLock',
        
        # Arrow keys
        'ArrowUp': 'ArrowUp',
        'ArrowDown': 'ArrowDown',
        'ArrowLeft': 'ArrowLeft',
        'ArrowRight': 'ArrowRight',
        
        # Function keys
        'F1': 'F1', 'F2': 'F2', 'F3': 'F3', 'F4': 'F4',
        'F5': 'F5', 'F6': 'F6', 'F7': 'F7', 'F8': 'F8',
        'F9': 'F9', 'F10': 'F10', 'F11': 'F11', 'F12': 'F12',
        
        # Modifier keys
        'Control': 'Control',
        'Alt': 'Alt',
        'Shift': 'Shift',
        'Meta': 'Meta',
        
        # Whitespace
        ' ': 'Space',
        'Space': 'Space',
    }
    
    _CODE_MAP: Dict[str, str] = {
        'Space': 'Space',
        'Enter': 'Enter',
        'Escape': 'Escape',
        'Tab': 'Tab',
        'Backspace': 'Backspace',
        'Delete': 'Delete',
        'Insert': 'Insert',
        'Home': 'Home',
        'End': 'End',
        'PageUp': 'PageUp',
        'PageDown': 'PageDown',
        'ArrowUp': 'ArrowUp',
        'ArrowDown': 'ArrowDown',
        'ArrowLeft': 'ArrowLeft',
        'ArrowRight': 'ArrowRight',
    }
    
    @classmethod
    def map_key(cls, key: str, code: Optional[str] = None) -> str:
        """
        Map JavaScript key name/code to Playwright key name.
        
        Args:
            key: JavaScript key value (e.g., 'a', 'Enter', 'Control')
            code: JavaScript key code (e.g., 'KeyA', 'Enter', 'ControlLeft')
            
        Returns:
            Playwright key name
        """
        # Check direct mapping first
        if key in cls._KEY_MAP:
            return cls._KEY_MAP[key]
        
        # Handle single character keys (letters, numbers, symbols)
        if len(key) == 1:
            # Playwright expects lowercase for letters, but Shift is handled separately
            return key.lower() if key.isalpha() else key
        
        # Handle code-based mapping for special cases
        if code and code in cls._CODE_MAP:
            return cls._CODE_MAP[code]
        
        # Default: return key as-is (Playwright may accept it)
        return key

