# Wiring Guide

Complete wiring instructions for connecting the TFT display to Raspberry Pi.

## ⚠️ Safety First

**CRITICAL WARNINGS:**
- **NEVER** reverse VCC and GND connections - this can permanently damage your Raspberry Pi or display
- **ALWAYS** double-check connections before applying power
- **USE** 3.3V power for your display unless specifically designed for 5V
- **DISCONNECT** power when making or changing connections
- **VERIFY** pin labels on your specific display module (names may vary)

## 📋 Required Components

### Hardware
- Raspberry Pi 3 Model B (or compatible)
- 1.8" TFT LCD Display 128x160 with ST7735R driver
- Jumper wires (male-to-female recommended for Pi header)
- Breadboard (optional, for prototyping)
- Multimeter (optional, for verifying connections)

### Tools
- Small screwdriver (if using screw terminals)
- Wire strippers (if using bare wire)
- Good lighting for seeing small pins

## 🔌 Pin Configuration

### TFT Display Pinout

Your TFT display should have 8 pins labeled something like:

```
Pin 1: VCC   (Power)
Pin 2: GND   (Ground)
Pin 3: RESET (Reset)
Pin 4: D/C   (Data/Command or A0)
Pin 5: SDA   (SPI Data or DIN)
Pin 6: SCK   (SPI Clock or CLK)
Pin 7: CS    (Chip Select)
Pin 8: LED   (Backlight)
```

**Note:** Pin names may vary slightly between manufacturers:
- VCC might be labeled VDD or 3.3V
- GND might be labeled GND or 0V
- RESET might be labeled RST
- D/C might be labeled A0 or DC
- SDA might be labeled DIN, MOSI, or SDI
- SCK might be labeled CLK or SCL
- CS might be labeled CS or SS
- LED might be labeled BL or LED+

### Raspberry Pi GPIO Header (40-pin)

```
   3V3  (1) (2)  5V
 GPIO2  (3) (4)  5V
 GPIO3  (5) (6)  GND
 GPIO4  (7) (8)  GPIO14
   GND  (9) (10) GPIO15
GPIO17 (11) (12) GPIO18
GPIO27 (13) (14) GND
GPIO22 (15) (16) GPIO23
   3V3 (17) (18) GPIO24
GPIO10 (19) (20) GND
 GPIO9 (21) (22) GPIO25
GPIO11 (23) (24) GPIO8
   GND (25) (26) GPIO7
 GPIO0 (27) (28) GPIO1
 GPIO5 (29) (30) GND
 GPIO6 (31) (32) GPIO12
GPIO13 (33) (34) GND
GPIO19 (35) (36) GPIO16
GPIO26 (37) (38) GPIO20
   GND (39) (40) GPIO21
```

## 🔗 Connection Table

| LCD Pin | LCD Name | Connect To | RPi Pin | RPi Function | Wire Color (suggested) |
|---------|-----------|------------|----------|--------------|------------------------|
| 1 | VCC | 3.3V Power | Pin 1 | 3V3 | Red |
| 2 | GND | Ground | Pin 6 | GND | Black |
| 3 | RESET | GPIO 24 | Pin 18 | GPIO 24 | Yellow |
| 4 | D/C or A0 | Data/Command | GPIO 23 | Pin 16 | Green |
| 5 | SDA or DIN | SPI Data (MOSI) | GPIO 10 | Pin 19 | Blue |
| 6 | SCK or CLK | SPI Clock (SCLK) | GPIO 11 | Pin 23 | Purple |
| 7 | CS | Chip Select (CE0) | GPIO 8 | Pin 24 | Orange |
| 8 | LED | Backlight (always-on) | 3.3V | Pin 1 | Red |

## 📐 Connection Diagram

```
TFT Display                    Raspberry Pi GPIO Header
┌─────────┐                 ┌───────────────────────┐
│ VCC  ◄──┼─Red─────────────┼──► Pin 1 (3.3V)      │
│ GND  ◄──┼─Black───────────┼──► Pin 6 (GND)       │
│ RST  ◄──┼─Yellow─────────┼──► Pin 18 (GPIO 24)  │
│ D/C  ◄──┼─Green──────────┼──► Pin 16 (GPIO 23)  │
│ SDA  ◄──┼─Blue───────────┼──► Pin 19 (GPIO 10)  │
│ SCK  ◄──┼─Purple────────┼──► Pin 23 (GPIO 11)  │
│ CS   ◄──┼─Orange─────────┼──► Pin 24 (GPIO 8)   │
│ LED  ◄──┼─Red───────────┼──► Pin 1 (3.3V)      │
└─────────┘                 └───────────────────────┘
```

## 🧪 Testing Connections

### Visual Inspection
1. **Check all connections** are secure
2. **Verify no loose wires** or bad solder joints
3. **Confirm no shorts** between adjacent pins
4. **Check for proper polarity** on power connections

### Multimeter Testing (optional)
1. **Set to continuity mode**
2. **Test VCC to GND**: Should NOT have continuity (no short)
3. **Test each connection**: Verify continuity between LCD pin and Pi pin
4. **Test for shorts**: Check adjacent pins don't have continuity

### Power-Up Test
1. **Disconnect any other devices** from GPIO header
2. **Connect power to Raspberry Pi**
3. **Check for smoke or unusual smells** (unplug immediately if present)
4. **Measure voltage** on VCC pin (should be ~3.3V)
5. **Look for LED backlight** on display (should be on)

## 🔍 Troubleshooting Wiring

### Display Not Lighting Up
**Possible causes:**
- VCC not connected to 3.3V
- GND not connected properly
- Backlight LED connection issue

**Solutions:**
1. Verify VCC is connected to Pin 1 (3.3V)
2. Verify GND is connected to Pin 6
3. Check LED connection to Pin 1
4. Test with multimeter for 3.3V on VCC pin

### White Screen Only
**Possible causes:**
- Missing or incorrect data connections
- SPI not enabled
- Display not initialized

**Solutions:**
1. Check SDA (Pin 19), SCK (Pin 23), CS (Pin 24) connections
2. Verify SPI is enabled: `ls /dev/spi*`
3. Check D/C (Pin 16) and RST (Pin 18) connections
4. Run test script to verify display initialization

### Flickering Display
**Possible causes:**
- Loose connections
- SPI speed too high
- Power supply insufficient

**Solutions:**
1. Reseat all connections
2. Ensure wires are making good contact
3. Check power supply can provide adequate current
4. Try shorter jumper wires

### Display Shows Random Patterns
**Possible causes:**
- Incorrect SPI configuration
- Wrong data connections
- Communication errors

**Solutions:**
1. Verify SDA connected to Pin 19 (GPIO 10)
2. Verify SCK connected to Pin 23 (GPIO 11)
3. Verify CS connected to Pin 24 (GPIO 8)
4. Check D/C connected to Pin 16 (GPIO 23)
5. Verify RST connected to Pin 18 (GPIO 24)

## 🔧 Alternative Wiring Options

### Using CE1 Instead of CE0
If you need to use CE1 (Pin 24 is busy):

| LCD Pin | Connect To | RPi Pin |
|---------|------------|----------|
| CS | GPIO 7 (CE1) | Pin 26 |

Then modify the code:
```python
serial = spi(port=0, device=1, gpio_DC=23, gpio_RST=24)
```

### Using Different GPIO for D/C or RST
If pins 23 or 24 are occupied:

```python
# Use GPIO 27 for D/C instead of 23
serial = spi(port=0, device=0, gpio_DC=27, gpio_RST=24)

# Use GPIO 22 for RST instead of 24
serial = spi(port=0, device=0, gpio_DC=23, gpio_RST=22)
```

### Always-On Backlight Alternative
If you want software control over backlight:

| LCD Pin | Connect To | RPi Pin |
|---------|------------|----------|
| LED | GPIO 18 | Pin 12 |

Then modify the code:
```python
device = st7735(serial, rotate=1, gpio_LIGHT=18)
device.backlight(True)  # Turn on
device.backlight(False) # Turn off
```

## 📞 Additional Resources

### Raspberry Pi GPIO References
- [Pinout Diagram](https://pinout.xyz/) - Interactive GPIO pinout
- [GPIO Documentation](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html)

### Display References
- [ST7735R Datasheet](https://www.crystalfontz.com/controllers/Sitronix/ST7735R.pdf)
- [luma.lcd ST7735 Documentation](https://luma-lcd.readthedocs.io/en/stable/api-documentation.html#st7735)

### Troubleshooting
- [Common Issues](TROUBLESHOOTING.md) - Comprehensive troubleshooting guide
- [Technical Documentation](TECHNICAL.md) - Detailed technical information

## 🎓 Best Practices

### Connection Quality
- Use crimped connectors for reliable connections
- Stranded wire more flexible than solid core
- Keep wire lengths short (under 15cm)
- Test connections before final assembly

### Power Safety
- Use current-limited power supply
- Add fuse or polyfuse for extra protection
- Monitor temperature during extended use
- Disconnect power before making changes

### Signal Integrity
- Keep SPI wires together (reduce noise)
- Avoid running wires near high-frequency signals
- Use twisted pair for longer runs
- Add decoupling capacitor if needed

---

**Version:** 1.0.0
**Last Updated:** 2026-04-06
