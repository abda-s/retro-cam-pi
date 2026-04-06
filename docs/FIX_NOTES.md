# Color and Orientation Fix Notes

## Issues Fixed

### Issue 1: Wrong Colors (BRG → RGB)
**Problem:** OV5647 camera captures in SGBRG10 (Sony 10-bit GBRG pattern), causing incorrect colors.

**Solution Implemented:** Added RGB channel swapping in camera_tft_display.py
```python
# After capturing frame, swap R and B channels
frame = frame[:, :, [2, 1, 0]]  # Swap R and B channels
```

**Technical Explanation:**
- Camera captures with Green-Blue-Red-Green (GBRG) pattern
- NumPy array comes in as [G, B, R] order
- We need [R, G, B] order for correct colors
- Swapping indices [2, 1, 0] reorders channels correctly

### Issue 2: Display Orientation (Vertical → Landscape)
**Problem:** Display orientation didn't match user's landscape preference.

**Solution Implemented:** Made rotation easily configurable with detailed options.

## Rotation Options

Edit `display_rotation` value in `camera_tft_display.py` (line ~42):

```python
# Display rotation options:
# 0 = 0° (portrait: 128x160)
# 1 = 90° (landscape: 160x128)
# 2 = 180° (portrait upside down: 128x160)
# 3 = 270° (landscape upside down: 160x128)
self.display_rotation = 0  # Change this value
```

### Testing Rotation Values

**To test different rotations:**

1. **Stop current application** (Ctrl+C)
2. **Edit the file:**
   ```bash
   nano ~/rpi-tft-camera/src/camera_tft_display.py
   ```
3. **Change rotation value** (try 0, 1, 2, or 3)
4. **Save and exit** (Ctrl+X, Y, Enter)
5. **Restart application:**
   ```bash
   python3 ~/rpi-tft-camera/src/camera_tft_display.py
   ```
6. **Find the value that gives correct orientation**

### Physical Display Considerations

**If none of the rotations work correctly:**
- Check if your TFT display is mounted rotated in its enclosure
- Verify the display board orientation
- Some displays have default rotation that conflicts with software rotation
- May need to physically rotate the display or case

## Verification

### Test Color Fix

**1. View the live feed:**
- Red objects should appear red (not blue/purple)
- Blue objects should appear blue (not red/purple)
- Green should remain green (middle channel, not swapped)

**2. Capture a test image:**
- Press 't' to capture
- Transfer image to computer
- Open in image viewer
- Verify colors are correct

### Test Orientation Fix

**1. Check display orientation:**
- Should match camera's landscape orientation (width > height)
- Image should not be stretched vertically
- Aspect ratio should be reasonably preserved

**2. Test with known objects:**
- Hold up a rectangular object (like a book)
- Verify it displays correctly on TFT
- Should not appear rotated or mirrored

## Troubleshooting

### Colors Still Wrong

**If colors are still incorrect after the fix:**

**Try different channel swap:**
```python
# Try swapping G and R instead
frame = frame[:, :, [0, 2, 1]]  # Try this
```

**Or try different swap pattern:**
```python
# Try BGR swap (common with some cameras)
frame = frame[:, :, [2, 1, 0]]  # Current (should work)
# Alternative:
frame = frame[:, :, [0, 1, 2]]  # No swap
# Alternative 2:
frame = frame[:, :, [1, 0, 2]]  # Swap R and G
```

### Orientation Still Wrong

**If display is still not in landscape mode:**

**Test each rotation value systematically:**
1. Try rotation=0 (current)
2. Try rotation=1 (original landscape attempt)
3. Try rotation=2 (180° from current)
4. Try rotation=3 (270° from current)

**Check physical mounting:**
- Is the display board installed rotated?
- Is the ribbon cable oriented correctly?
- Is the case designed for vertical or horizontal mounting?

**Consider camera orientation:**
- Try rotating the camera physically
- Check if camera module is mounted correctly

## Additional Notes

### Performance Impact

**Color swap operation:** Minimal performance impact
- Single numpy array indexing operation
- O(1) complexity for each frame
- Negligible effect on 8-12 FPS target

### Future Improvements

**Automatic color calibration:**
- Add test pattern generation
- Allow user to verify colors
- Auto-select correct channel swap

**Orientation detection:**
- Add auto-detection based on aspect ratio
- Or allow runtime rotation switching with keyboard

---

**Version:** 1.0.1
**Last Updated:** 2026-04-06
