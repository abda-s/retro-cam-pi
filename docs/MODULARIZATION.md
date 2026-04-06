# Modularization Guide (v4.0.0)

This document explains the refactoring from v3.0.0 (single monolithic file) to v4.0.0 (modular architecture).

## Why Modularization?

The v3.0.0 `main.py` had ~460 lines handling:
- Camera worker logic
- Process worker logic  
- Display initialization
- Image capture/save
- Configuration loading

This violated **Single Responsibility Principle** - each module should do one thing well.

## New Module Structure

```
src/
├── __init__.py           # Package exports
├── main.py               # Entry point only (~150 lines)
├── camera_worker.py      # Capture process (~90 lines)
├── process_worker.py     # Resize process (~70 lines)
├── display_manager.py   # ST7735 handling (~180 lines)
├── capture_manager.py   # Image save/count (~200 lines)
├── config_manager.py    # Configuration (~80 lines)
└── shared.py            # Constants (~30 lines)
```

## Module Responsibilities

### camera_worker.py

**Purpose**: Capture frames from Picamera2 in a separate process.

**Public API**:
```python
def capture_worker(
    capture_queue_save: Queue,
    capture_queue_display: Queue,
    capture_count: Value,
    running_flag: Value,
    capture_resolution: Tuple[int, int],
) -> None
```

**Responsibilities**:
- Initialize Picamera2
- Capture RGB888 frames
- BGR→RGB channel swap
- Push to queues (with overflow handling)

### process_worker.py

**Purpose**: Resize frames using OpenCV cv2 in a separate process.

**Public API**:
```python
def process_worker(
    capture_queue_display: Queue,
    display_queue: Queue,
    running_flag: Value,
    display_size: Tuple[int, int],
) -> None
```

**Responsibilities**:
- Get full-res frames from capture queue
- Resize to display resolution using cv2.INTER_LINEAR
- Push to display queue

### display_manager.py

**Purpose**: Handle ST7735 TFT display operations.

**Public API**:
```python
class DisplayManager:
    def initialize(self) -> bool: ...
    def display_frame(self, image: Image.Image) -> None: ...
    def show_error(self, error_msg: str) -> None: ...
    def show_message(self, message: str, duration: float = 2.0) -> None: ...
    def cleanup(self) -> None: ...
    
    @property
    def width(self) -> int: ...
    def height(self) -> int: ...
    def size(self) -> Tuple[int, int]: ...
```

**Responsibilities**:
- SPI initialization (40 MHz → 8 MHz fallback)
- Display rotation configuration
- Frame rendering via luma
- Error display
- Resource cleanup

### capture_manager.py

**Purpose**: Manage image capture and saving.

**Public API**:
```python
class CaptureManager:
    def capture_image(...) -> Tuple[bool, Optional[Path]]: ...
    def save_frame(frame: np.ndarray, filename: Path) -> bool: ...
    def set_feedback(message: str) -> None: ...
    def is_feedback_active() -> bool: ...
```

**Responsibilities**:
- Save full-resolution images
- Fallback queue strategy for reliable capture
- Feedback overlay timing
- Capture count tracking

### config_manager.py

**Purpose**: Load and provide configuration.

**Public API**:
```python
class Config:
    # Display settings
    display_resolution: Tuple[int, int]
    display_rotation: int
    spi_speed_hz: int
    # ... and more
    
    def get_display_size(self) -> Tuple[int, int]: ...
    def get_capture_size(self) -> Tuple[int, int]: ...

class ConfigLoader:
    @staticmethod
    def load() -> Config: ...
```

**Responsibilities**:
- Default configuration values
- Environment variable overrides
- Directory creation

### shared.py

**Purpose**: Constants shared across modules.

**Contents**:
- Display resolution
- SPI speeds (40 MHz, 8 MHz fallback)
- Queue max sizes
- Feedback duration
- File format defaults

### main.py (Entry Point)

**Purpose**: Orchestrate all modules.

**Responsibilities**:
- Create Config instance
- Initialize DisplayManager
- Initialize CaptureManager
- Start/stop worker processes
- Main display loop
- FPS tracking

## Best Practices Applied

1. **Single Responsibility**: Each module does one thing
2. **Dependency Injection**: Config passed to classes
3. **Type Hints**: Full typing throughout
4. **Docstrings**: Every function/class documented
5. **Properties**: Using `@property` for computed values
6. **Graceful Fallbacks**: 40 MHz → 8 MHz SPI
7. **Error Handling**: Try/except with specific exceptions

## Migration from v3.0.0

If you have custom code based on v3.0.0:

**Old**:
```python
# v3.0.0 - all in one file
from camera_tft_display import OptimizedCameraDisplay
app = OptimizedCameraDisplay()
app.run()
```

**New**:
```python
# v4.0.0 - modular
from config_manager import Config
from display_manager import DisplayManager
from capture_manager import CaptureManager

config = Config()
display = DisplayManager(rotation=config.display_rotation)
capture = CaptureManager(config.save_directory)
# ... build your own orchestration
```

Or simply use the provided entry point:
```python
from main import main
main()
```

## Testing

All modules compile successfully:
```bash
python3 -m py_compile src/*.py
```

## Extending the Project

Want to add a feature? Here's where to put it:

- **New camera sensor** → Modify `camera_worker.py`
- **Different display driver** → Modify `display_manager.py` 
- **Add timestamp overlay** → Modify `capture_manager.py`
- **New capture trigger** → Add to `main.py` input handling
- **Config from file** → Modify `config_manager.py`

---

**Version:** 4.0.0
**Date:** 2026-04-06