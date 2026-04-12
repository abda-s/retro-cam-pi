# Wiring Guide

Complete wiring for ST7735R TFT display to Raspberry Pi.

## Safety

**WARNING:** Reverse VCC/GND can damage hardware. Double-check all connections before powering on.

## Pin Configuration

### TFT Display → Raspberry Pi GPIO

| LCD Pin | Name | Connect To | RPi Pin | GPIO |
|---------|------|------------|---------|------|
| 1 | VCC | 3.3V Power | Pin 1 | - |
| 2 | GND | Ground | Pin 6 | - |
| 3 | RESET | GPIO 24 | Pin 18 | 24 |
| 4 | D/C | Data/Command | Pin 16 | 23 |
| 5 | SDA | SPI Data (MOSI) | Pin 19 | 10 |
| 6 | SCK | SPI Clock | Pin 23 | 11 |
| 7 | CS | Chip Select (CE0) | Pin 24 | 8 |
| 8 | LED | Backlight | Pin 1 | - |

## Physical Button Wiring (Retro Camera Controls)

Use active-low wiring with internal pull-ups:

- One side of each button to GPIO pin
- Other side of each button to GND
- App config uses `GPIO.PUD_UP` and treats LOW as "pressed"

| Control | GPIO | Pin |
|---------|------|-----|
| SHUTTER | 5 | 29 |
| MODE (PHOTO/VIDEO) | 21 | 40 |
| VIEW (LIVE/VIEW) | 13 | 33 |
| NEXT | 19 | 35 |
| PREV | 26 | 37 |

Recommended ground: Pin 39 (common ground rail for all buttons)

Behavior note:
- MODE short press toggles PHOTO/VIDEO in LIVE mode
- MODE long press deletes current file in VIEW mode

Implementation note:
- MODE primary pin is GPIO 21 in current build.
- MODE fallback pins supported in software: GPIO 6, GPIO 16, GPIO 20.

## Wiring Diagram

```
TFT Display                    Raspberry Pi
┌─────────┐                 ┌───────────────┐
│ VCC  ◄──┼── Red ────────┼──► Pin 1 (3.3V)│
│ GND  ◄──┼── Black ──────┼──► Pin 6 (GND) │
│ RST  ◄──┼── Yellow ─────┼──► Pin 18 (24)  │
│ D/C  ◄──┼── Green ──────┼──► Pin 16 (23)  │
│ SDA  ◄──┼── Blue ───────┼──► Pin 19 (10) │
│ SCK  ◄──┼── Purple ─────┼──► Pin 23 (11) │
│ CS   ◄──┼── Orange ─────┼──► Pin 24 (8)   │
│ LED  ◄──┼── Red ────────┼──► Pin 1 (3.3V)│
└─────────┘                 └───────────────┘
```

## Testing

### Check SPI Enabled
```bash
ls /dev/spi*
# Should show: /dev/spidev0.0 /dev/spidev0.1
```

If not found:
```bash
sudo raspi-config
# Interface Options → SPI → Enable
```

### Check Permissions
```bash
groups cam
# Should include: spi, gpio, video
```

### Test Display Initialization
```bash
python3 -c "
from luma.core.interface.serial import spi
from luma.lcd.device import st7735
serial = spi(port=0, device=0, gpio_DC=23, gpio_RST=24)
device = st7735(serial, rotate=2)
print(f'Display OK: {device.width}x{device.height}')
"
```

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| White screen | SPI not enabled | Enable SPI in raspi-config |
| Black screen | VCC not connected | Check Pin 1 connection |
| Flickering | Loose wires | Reseat all connections |
| Wrong colors | D/C pin wrong | Check GPIO 23 |

## Alternative Wiring

### CE1 Instead of CE0
| LCD Pin | Alternative |
|--------|-------------|
| CS | GPIO 7 (Pin 26) |

Code change:
```python
serial = spi(port=0, device=1, gpio_DC=23, gpio_RST=24)
```

### Different Control Pins
```python
# Use GPIO 22 for RST instead
serial = spi(port=0, device=0, gpio_DC=23, gpio_RST=22)
```
