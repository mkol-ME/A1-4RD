# V2 base display: preliminary interface

Goal: add an approximately four-inch screen to the base that shows Alfred's
spoken reply as readable text. Placement, touch support, and exact module are
still open. The initial working assumption is a screen on the front face that
shows captions without touch controls.

## Connection and data path

- Keep the Pi Zero 2 W for now. It exposes mini HDMI, not a DSI display port.
  A four-inch HDMI LCD can use the Pi's video output while the GPIO header stays
  available for I2S audio, servos, button, and indicator.
- Supply the LCD from a protected 5 V branch and include its backlight draw in
  the measured power budget. Do not power it through a thin Pi jumper wire in
  the final assembly. Route a short mini-HDMI cable with connector clearance,
  bend radius, and strain relief inside the base.
- `brain/voice_server.py` already sends `{"text": ..., "audio": ...}` for each
  voiced sentence. `client/talk.py` reads these frames and queues the audio.
  The Pi client can hand each `text` value to a local caption view as the audio
  is queued. This gives sentence-level captions. Word-by-word highlighting
  would need timing data that the current server does not send.
- The caption view should clear when a new turn begins, wrap and scroll long
  replies, show the most recent sentence in large type, and turn the backlight
  down when idle. Treat any text from private memory as visible to everyone
  who can see the base.

## Mechanical implications

- Four inches is a diagonal, not a panel footprint. Select a real module and
  use its panel, PCB, mounting-hole, connector, and cable drawings before
  fixing the base diameter or front angle. A landscape display will likely
  make the base wider than the six-inch figure.
- Keep the display/bezel replaceable. A removable front panel lets a first
  body be built without a screen while preserving a V2 upgrade path.
- Keep the speaker outlet and mic port away from the LCD cavity. The screen
  panel should not become the speaker baffle or block the acoustic path.

## Prototype test

Before committing to a screen or larger base, connect a small HDMI monitor to
the Pi and render captions from the existing sentence frames. Check text size
at desk viewing distance, first-caption timing, scrolling during long replies,
and simultaneous audio playback. Then bench-test the chosen four-inch module
for its actual current and connector clearance.

One example to evaluate is the [Waveshare 4inch HDMI LCD](https://www.waveshare.com/wiki/4inch_HDMI_LCD),
an 800×480-class IPS module (native panel orientation is 480×800) that requires
an HDMI cable on the Zero 2 W. Its resistive touch function uses additional
GPIO/SPI resources, so leave touch disconnected if the screen only displays
captions. This is a candidate, not a selected part.

Sources: [Pi Zero 2 W interfaces](https://www.raspberrypi.com/products/raspberry-pi-zero-2-w/),
[Waveshare module guide](https://www.waveshare.com/wiki/4inch_HDMI_LCD).
