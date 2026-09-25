# Pi client hardware setup — module prototype A

The server continues to perform transcription, language generation and voice synthesis. No server model changes are needed.

The supplied audio overlay and smoke test are adapted from the previous hardware package. They target the Raspberry Pi voiceHAT codec/machine interface at 48 kHz, stereo, signed 32-bit little-endian audio. **The overlay has not been compiled or boot-tested on a physical Pi in this task.** Verify the installed kernel provides the required drivers and symbols.

1. Install Raspberry Pi OS Lite. Install `device-tree-compiler` and `alsa-utils` using its package manager.
2. Confirm the kernel has `snd_soc_googlevoicehat_codec` and `snd_soc_rpi_simple_soundcard`, either modules or built in.
3. Run `sh build-overlay.sh`. If successful, copy `alfred-audio.dtbo` into the active boot overlays directory, normally `/boot/firmware/overlays/`. Back up the boot configuration before editing it.
4. Use this configuration, removing conflicting audio overlays:

```ini
dtparam=audio=off
dtparam=i2c_arm=on
dtoverlay=alfred-audio
gpio=22=op,dh
```

GPIO17 is owned by the audio driver for amplifier SD. GPIO22 is PCA9685 OE, HIGH=disabled. Do not install the former GPIO12 PWM overlay or the former GPIO22 LOW-at-boot setting.

5. Reboot and inspect `arecord -l` and `aplay -l`. Run the smoke test using its `--help` instructions and the actual card name. It plays a quiet tone and captures the mic; listen to the recorded file and inspect logs, not just the exit code.
6. Configure the existing `listen.py`/`talk.py` audio devices. Native hardware format is 48 kHz stereo S32_LE; use tested conversion to the client's expected format. Mic data is on the left channel. Do not assume the default audio device or channel mapping is correct.
7. Add PCA9685 support using a maintained I2C library. Initialize OE HIGH, initialize at 50 Hz with unused channels off, set the actual calibrated channel-0 pulse, then enable OE. Keep the identity button on GPIO27. A completed servo integration into the Alfred client is a separate target-hardware step; this package does not silently modify the working client.

The old PCB supply-good/fault pins and hardware arm latch do not exist in this module prototype. Read ../Wiring.md before using any old servo code.

Kernel references reviewed in the prior design:

- https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.12.y/sound/soc/bcm/googlevoicehat-codec.c
- https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.12.y/sound/soc/bcm/rpi-simple-soundcard.c
- https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.12.y/arch/arm/boot/dts/overlays/googlevoicehat-soundcard-overlay.dts
