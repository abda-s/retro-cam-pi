# RPi TFT Camera Display

Display live camera feed on a 128x160 TFT LCD screen with instant image capture functionality.

## 🎯 Features

- **Live Video Feed**: Real-time camera display on 128x160 TFT screen (12-22 FPS with multi-core)
- **Instant Capture**: Press 't' to capture high-resolution images instantly
- **Smart Storage**: Captures saved at original resolution (320x240 PNG) - full quality!
- **Visual Feedback**: On-screen confirmation when images are saved
- **Graceful Exit**: Clean shutdown with Ctrl+C
- **Multi-Core Optimization**: Uses 3-4 Raspberry Pi 3B cores for 2.2x performance
- **Separate Capture Queues**: Independent queues for saving (320x240) and display processing
- **Color Correction**: BRG to RGB conversion for correct colors
- **Display Rotation**: 180° rotation option for proper orientation

## 📋 Requirements

### Hardware
- Raspberry Pi 3 Model B (or any Pi with camera support)
- Raspberry Pi Camera Module (OV5647 tested)
- 1.8" TFT LCD Display 128x160 with ST7735R driver
- Jumper wires for connections
- MicroSD card (16GB+ recommended)
- Power supply for Raspberry Pi

### Software
- Raspberry Pi OS (Bookworm or newer)
- Python 3.13+
- libcamera (v0.6.0+)
- Network connection (for initial setup)

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd ~/rpi-tft-camera
chmod +x setup.sh
sudo ./setup.sh
```

### 2. Log Out and Log In
**Required** for group permissions to take effect.

### 3. Run the Application

```bash
cd ~/rpi-tft-camera/src
python3 camera_tft_display.py
```

## 📖 Usage

### Application Options

**Standard Version (Single-Threaded):**
- File: `camera_tft_display.py`
- Performance: 8-10 FPS
- Cores used: 1 (25% utilization)
- Memory: ~6MB

**Optimized Version (Multi-Core with Separate Capture Queues):**
- File: `camera_tft_optimized.py`
- Performance: 18-22 FPS (2.2x faster!)
- Cores used: 3-4 (75% utilization)
- Memory: ~12MB
- Features: Separate capture queues for saving full-resolution images

### Controls
- **'t' key**: Capture current frame and save as PNG (320x240 full resolution)
- **Ctrl+C**: Exit application gracefully

### What Happens When You Press 't' (Optimized Version)

1. Live feed continues smoothly (no pause!)
2. Current frame is captured at original resolution (320x240) from Queue A
3. Image is saved to `~/Pictures/captures/capture_YYYYMMDD_HHMMSS.png`
4. "Saved!" message appears on screen
5. Live feed continues without interruption

### File Storage

- **Location**: `~/Pictures/captures/`
- **Format**: PNG (lossless)
- **Resolution**: 320x240 (original capture resolution - full quality!)
- **Naming**: `capture_YYYYMMDD_HHMMSS.png`

### Performance Comparison

| Version | FPS | Cores | Memory | Features |
|---------|-----|--------|---------|-----------|
| Standard | 8-10 | 1 (25%) | 6MB | Basic capture |
| Optimized | 18-22 | 3-4 (75%) | 12MB | Multi-core, separate queues, full-res saves |

## 🔧 Hardware Setup

### TFT Display Wiring

Connect your TFT display to Raspberry Pi GPIO header:

| LCD Pin | Name | Connect To | RPi Pin |
|---------|------|------------|---------|
| 1 | VCC | 3.3V Power | Pin 1 |
| 2 | GND | Ground | Pin 6 |
| 3 | RESET | GPIO 24 | Pin 18 |
| 4 | D/C or A0 | Data/Command | GPIO 23 | Pin 16 |
| 5 | SDA or DIN | SPI Data (MOSI) | GPIO 10 | Pin 19 |
| 6 | SCK or CLK | SPI Clock (SCLK) | GPIO 11 | Pin 23 |
| 7 | CS | Chip Select (CE0) | GPIO 8 | Pin 24 |
| 8 | LED | Backlight | 3.3V | Pin 1 |

**⚠️ Important Safety Notes:**
- Double-check VCC and GND connections
- Use 3.3V, NOT 5V (unless your display specifically requires 5V)
- Verify pin labels on your specific display module
- Triple-check all connections before powering on

### Camera Connection

- Connect camera module to camera ribbon cable port on Raspberry Pi
- Ensure ribbon cable is inserted fully and locked
- Camera should be detected automatically

## 📁 Project Structure

```
rpi-tft-camera/
├── README.md                      # This file
├── TECHNICAL.md                   # Detailed technical documentation
├── setup.sh                       # Main installation script
├── .gitignore                     # Git ignore patterns
├── src/
│   ├── camera_tft_display.py       # Main application
│   ├── requirements.txt            # Python dependencies
│   └── install_dependencies.sh    # Dependency installer
├── config/
│   └── display_config.py          # Configuration parameters
└── docs/
    ├── WIRING.md                  # Complete wiring guide
    └── TROUBLESHOOTING.md        # Common issues & solutions
```

## ⚙️ Configuration

Edit `config/display_config.py` to customize:

- Camera capture resolution
- Display rotation
- Save location and format
- Performance settings
- Error handling options

## 🔍 Troubleshooting

### Application won't exit with Ctrl+C
- Check if any processes are hung: `ps aux | grep camera_tft`
- Kill manually if needed: `killall python3` (last resort)
- Ensure all workers check shutdown_requested flag
- Wait 3-5 seconds after Ctrl+C for clean shutdown

### No display output
- Check wiring connections
- Verify SPI is enabled: `ls /dev/spi*`
- Check permissions: `groups cam` (should include spi, gpio)

### Camera not working
- Verify camera connection: `rpicam-still -o test.jpg`
- Check camera permissions: `groups cam` (should include video)
- Ensure libcamera is installed: `rpicam-still --list-cameras`
- Stop any other camera applications: `killall rpicam-still`

### Low performance
- Lower capture resolution in `config/display_config.py`
- Close other applications
- Check CPU usage: `top`

### High memory usage
- Check queue sizes: Monitor "Queue Sizes" output
- Reduce queue maxsize in script (currently 2 per queue)
- Restart application periodically if needed

For more detailed troubleshooting, see `docs/TROUBLESHOOTING.md`.

## 📊 Performance

Typical performance on Raspberry Pi 3 Model B:

| Setting | Resolution | FPS | Quality | Notes |
|---------|-------------|------|---------|--------|
| Default | 320x240 → 128x160 | 8-12 | Good | Balanced |
| High | 640x480 → 128x160 | 5-8 | Better | Slower |
| Low | 160x120 → 128x160 | 10-15 | Lower | Faster |

## 🤝 Contributing

Contributions welcome! Please feel free to submit issues or pull requests.

## 📄 License

This project is provided as-is for educational and hobbyist use.

## 📞 Support

For detailed technical information, see:
- `TECHNICAL.md` - System architecture and implementation details
- `docs/WIRING.md` - Complete wiring guide
- `docs/TROUBLESHOOTING.md` - Common issues and solutions

## 🔗 Resources

- [Picamera2 Documentation](https://github.com/raspberrypi/picamera2)
- [luma.lcd Documentation](https://luma-lcd.readthedocs.io/)
- [Raspberry Pi Camera Documentation](https://www.raspberrypi.com/documentation/computers/camera.html)

## 🙏 Acknowledgments

- Picamera2 library by Raspberry Pi Foundation
- luma.lcd library by Richard Hull
- libcamera by Raspberry Pi Foundation
- ST7735 display driver integration

---

**Version:** 1.0.0
**Last Updated:** 2026-04-06
