# RPi TFT Camera Display

Display live camera feed on a 128x160 TFT LCD screen with instant image capture functionality.

## 🎯 Features

- **Live Video Feed**: Real-time camera display on 128x160 TFT screen (8-12 FPS)
- **Instant Capture**: Press 't' to capture high-resolution images instantly
- **Smart Storage**: Captures saved at original resolution (320x240 PNG)
- **Visual Feedback**: On-screen confirmation when images are saved
- **Graceful Exit**: Clean shutdown with Ctrl+C
- **Optimized Performance**: Efficient processing for smooth video playback

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

### Controls
- **'t' key**: Capture current frame and save as PNG
- **Ctrl+C**: Exit application gracefully

### What Happens When You Press 't'

1. Live feed pauses momentarily
2. Current frame is captured at original resolution (320x240)
3. Image is saved to `~/Pictures/captures/capture_YYYYMMDD_HHMMSS.png`
4. "Saved!" message appears on screen
5. Live feed resumes after 2 seconds

### File Storage

- **Location**: `~/Pictures/captures/`
- **Format**: PNG (lossless)
- **Resolution**: 320x240 (original capture resolution)
- **Naming**: `capture_YYYYMMDD_HHMMSS.png`

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

### No display output
- Check wiring connections
- Verify SPI is enabled: `ls /dev/spi*`
- Check permissions: `groups cam` (should include spi, gpio)

### Camera not working
- Verify camera connection: `rpicam-still -o test.jpg`
- Check camera permissions: `groups cam` (should include video)
- Ensure libcamera is installed: `rpicam-still --list-cameras`

### Low performance
- Lower capture resolution in `config/display_config.py`
- Close other applications
- Check CPU usage: `top`

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
