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