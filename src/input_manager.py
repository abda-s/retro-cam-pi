"""Input manager for rpi-tft-camera.

Provides non-blocking key detection from stdin.
"""

import select
import sys
from typing import Optional


class InputManager:
    """Manages keyboard input with non-blocking detection."""
    
    def __init__(self):
        """Initialize input manager."""
        self._last_key: Optional[str] = None
    
    def check_for_input(self) -> Optional[str]:
        """Check for key input (non-blocking).
        
        Uses select.select() to poll stdin without blocking.
        
        Returns:
            Key character if available, None otherwise
        """
        if select.select([sys.stdin], [], [], 0)[0]:
            try:
                key = sys.stdin.read(1)
                key_lower = key.lower()
                self._last_key = key_lower
                return key_lower
            except Exception:
                pass
        return None
    
    def wait_for_key(self, timeout: float = 0.1) -> Optional[str]:
        """Wait for a key press with timeout.
        
        Args:
            timeout: Timeout in seconds
        
        Returns:
            Key character if pressed within timeout, None otherwise
        """
        if select.select([sys.stdin], [], [], timeout)[0]:
            try:
                key = sys.stdin.read(1)
                return key.lower()
            except Exception:
                pass
        return None
    
    def poll_for_key(self, max_wait: float = 5.0) -> Optional[str]:
        """Poll for a key press for a duration.
        
        Args:
            max_wait: Maximum wait time in seconds
        
        Returns:
            Key character if pressed, None if timeout exceeded
        """
        start = __import__('time').time()
        while __import__('time').time() - start < max_wait:
            key = self.check_for_input()
            if key:
                return key
            __import__('time').sleep(0.01)
        return None
    
    @property
    def last_key(self) -> Optional[str]:
        """Get the last key that was pressed."""
        return self._last_key
