# Alfred audio and jaw bring-up

This package adds a concrete audio integration path. It is **source-reviewed, not tested on a physical Alfred or compiled on this Windows host**. Use Raspberry Pi OS with the Raspberry Pi kernel and the existing voiceHAT codec/machine modules. Review was against `rpi-6.12.y`; verify compatibility for the image you install.

The voiceHAT codec supports simultaneous 48 kHz stereo S32_LE capture/playback and controls an amplifier enable GPIO. The companion machine driver selects standard I2S and derives a 64-bit frame for 32-bit samples. Those interfaces match Alfred's intended clocks and data wiring. The included overlay changes amplifier enable to **GPIO17**. Do not use the unmodified stock overlay, which drives GPIO16 instead.

## Setup on the Pi

1. Install `device-tree-compiler`, `alsa-utils` and Python 3 using the Pi's package manager. Confirm `modinfo snd_soc_googlevoicehat_codec` and `modinfo snd_soc_rpi_simple_soundcard` find the modules; built-in drivers may instead appear in the kernel configuration. If neither modules nor built-ins exist, use a supported Raspberry Pi kernel before proceeding.
2. Run `sh build-overlay.sh` in this directory. Stop if dtc reports errors. Copy the resulting `alfred-audio.dtbo` to `/boot/firmware/overlays/` (older installations use `/boot/overlays/`). Keep a backup of the boot configuration before editing it.
3. Add the following to the active boot configuration (`/boot/firmware/config.txt` on current Raspberry Pi OS):

```ini
dtparam=audio=off
dtoverlay=alfred-audio
gpio=22=op,dl
# GPIO12 uses hardware PWM0, separate from the I2S pins.
dtoverlay=pwm,pin=12,func=4
```

Remove conflicting I2S audio overlays and do not enable PWM analog audio. Reboot manually after reviewing the file. No installation or reboot is performed by the supplied build script.

4. Use `arecord -l` and `aplay -l` to identify the same voiceHAT card in both directions. Use its actual ALSA ID; do not assume it is card 0. The kernel card name contains `googlevoicehat` because the existing driver is reused.
5. With the servo disconnected and hardware voltages checked, run `python3 audio-smoke-test.py --device hw:YOUR_CARD_ID,0`. This intentionally emits a quiet test tone and records two short local WAV files. Avoid other audio clients during the test. The script refuses to overwrite its output folder; choose a new `--output` for each run.

## Application contract

- Use 48,000 Hz, two 32-bit slots, S32_LE. Expected LRCLK is 48 kHz and BCLK 3.072 MHz.
- Capture contains the microphone in the **left** channel. Extract that channel for recognition; the right channel is not a second microphone. The mic has 24 useful bits within the 32-bit slot.
- Playback also uses the **left** channel. Duplicate mono speech into both slots or explicitly place it on the left.
- Start at -12 dBFS or lower for speech and raise only after testing. Revision D's 9 dB hardware gain can approach the speaker's 3 W rating at full scale, but clean output depends on supply and load. The smoke test uses -30 dBFS.
- The kernel owns GPIO17. Do not claim it in the Alfred application at the same time.
- Add playback-reference acoustic echo cancellation for listening while speaking. Full duplex alone does not suppress the loudspeaker or servo noise.
- Test continuous capture while repeatedly starting/stopping playback, then the reverse. Run a 30-minute combined test with Wi-Fi and supervised jaw movement; log ALSA errors, `vcgencmd get_throttled`, and minimum measured Pi-header voltage.

## Jaw control contract

GPIO22 requests servo power; GPIO25 reports supply-good; GPIO27 reports active-low servo fault. GPIO12 is PWM0. Keep request low on startup and shutdown. Prepare a 50 Hz PWM waveform at a calibrated neutral pulse before requesting power. Use hardware PWM through the kernel; do not use a PCM-timed servo library while audio uses I2S.

Revision D has a hardware arm latch. First drive GPIO22 LOW. Require GPIO25 supply-good HIGH for at least 100 ms and GPIO22 LOW for at least 10 ms before a deliberate GPIO22 rising edge. A request issued while supply-good is LOW will not arm later when the rail recovers. The supervisor also applies about 107 ms nominal recovery qualification. Check the fault input after the servo rail has completed its approximately 12 ms startup ramp. Clear GPIO22 immediately if supply-good falls or a powered-servo fault appears, and require a deliberate retry. After a detected undervoltage fault, hardware remains disarmed even if GPIO22 stayed HIGH. Deliberately clear it LOW and repeat qualification only after investigating the fault. Do not auto-retry a jam in a tight loop. On application exit, clear the power request before releasing PWM/GPIO ownership.

Start with the linkage detached. A 1500 us pulse is a conventional starting point, not a guarantee of Alfred's safe jaw position. Measure and store the real closed/open limits; never assume the full 500-2500 us range is safe. No jaw movement script is included because the mechanical limits have not been supplied.

## Sources

- [Raspberry Pi voiceHAT codec](https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.12.y/sound/soc/bcm/googlevoicehat-codec.c)
- [Raspberry Pi machine driver](https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.12.y/sound/soc/bcm/rpi-simple-soundcard.c)
- [Raspberry Pi voiceHAT overlay](https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.12.y/arch/arm/boot/dts/overlays/googlevoicehat-soundcard-overlay.dts)

The DTS uses the existing GPL kernel interfaces and carries a GPL-2.0-only identifier. It identifies the compatible interface; it does not claim Alfred is a Google-manufactured board.

## Offline logic check

Run `python3 validate-hardware-logic.py` from any directory to repeat the latch truth-table sequence checks and static threshold calculations. This reads the package design-data.json. It neither accesses GPIO nor substitutes for physical fault injection.
