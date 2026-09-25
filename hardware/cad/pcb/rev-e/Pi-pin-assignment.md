# Pi header — physical pin numbers

View this as a pin-number table, not a carrier-bottom physical drawing. All unused GPIO pins are unconnected on the carrier.

| Physical pin | BCM GPIO | Carrier net | Function |
|---:|---:|---|---|
| 1 | — | PI_3V3 | 3.3 V supplied by Pi |
| 2 | — | PI_5V | 5 V into Pi |
| 3 | 2 | NC | I2C1 available; no carrier connection |
| 4 | — | PI_5V | 5 V into Pi |
| 5 | 3 | NC | I2C1 available; no carrier connection |
| 6 | — | GND | Ground |
| 7 | 4 | NC | Unused; no carrier connection |
| 8 | 14 | NC | Unused; no carrier connection |
| 9 | — | GND | Ground |
| 10 | 15 | NC | Unused; no carrier connection |
| 11 | 17 | AMP_ENABLE | Amplifier enable, high = left playback |
| 12 | 18 | BCLK_PI | PCM_CLK / shared BCLK output |
| 13 | 27 | SERVO_FAULT_N | Servo fault input, active low |
| 14 | — | GND | Ground |
| 15 | 22 | SERVO_REQUEST | Servo power request output |
| 16 | 23 | BUTTON_N | Button input, active low |
| 17 | — | NC | Unused; no carrier connection |
| 18 | 24 | LED_GPIO | Status LED output |
| 19 | 10 | NC | Unused; no carrier connection |
| 20 | — | GND | Ground |
| 21 | 9 | NC | Unused; no carrier connection |
| 22 | 25 | SUPPLY_OK | Supply-good input |
| 23 | 11 | NC | Unused; no carrier connection |
| 24 | 8 | NC | Unused; no carrier connection |
| 25 | — | GND | Ground |
| 26 | 7 | NC | Unused; no carrier connection |
| 27 | 0 | NC | Reserved HAT EEPROM ID bus; no carrier connection |
| 28 | 1 | NC | Reserved HAT EEPROM ID bus; no carrier connection |
| 29 | 5 | NC | Unused; no carrier connection |
| 30 | — | GND | Ground |
| 31 | 6 | NC | Unused; no carrier connection |
| 32 | 12 | JAW_PWM | PWM0 / hardware jaw PWM |
| 33 | 13 | NC | Unused; no carrier connection |
| 34 | — | GND | Ground |
| 35 | 19 | LRCLK_PI | PCM_FS / shared LRCLK output |
| 36 | 16 | NC | Unused; no carrier connection |
| 37 | 26 | NC | Unused; no carrier connection |
| 38 | 20 | MIC_DATA_PI | PCM_DIN / microphone data input |
| 39 | — | GND | Ground |
| 40 | 21 | AMP_DATA_PI | PCM_DOUT / amplifier data output |

No EEPROM or I2C-addressed device is attached to the Pi. Pins 27/28 are untouched. The standalone PD controller HPI bus is also unconnected. GPIO12 PWM0 does not consume GPIO18/19/20/21 PCM signals. Disable PWM analog audio and do not run PCM-based servo timing libraries concurrently with I2S.
