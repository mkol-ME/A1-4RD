# Alfred module prototype — wiring

Use the Pi's **physical header pin numbers** in this table; BCM numbers identify signals in software. Wire with power removed. The server connection is Wi-Fi plus the project's existing SSH tunnel.

| Pi physical pin | BCM / function | Connection |
|---:|---|---|
| 1 | 3.3 V | Mic 3V/VDD; PCA9685 VCC; OE pull-up and button pull-up |
| 2 and 4 | 5 V input | Same fused Pi/audio +5 V branch, split to both contacts |
| 6 and 9 | Ground | Star ground, split to both contacts; all module grounds common |
| 3 | GPIO2 / SDA | PCA9685 SDA |
| 5 | GPIO3 / SCL | PCA9685 SCL |
| 12 | GPIO18 / PCM clock | Mic BCLK and amplifier BCLK |
| 35 | GPIO19 / PCM frame | Mic LRCL/WS and amplifier LRC |
| 38 | GPIO20 / PCM input | Mic DOUT |
| 40 | GPIO21 / PCM output | Amplifier DIN |
| 11 | GPIO17 | Amplifier SD, controlled by the included audio overlay |
| 15 | GPIO22 | PCA9685 OE, active HIGH disables servo pulses |
| 13 | GPIO27 | Identity button input; normally open switch to ground |

Additional connections:

- Mic SEL to GND for the left channel. The mic is a 3.3 V part; never connect its supply or logic to 5 V.
- Amplifier VIN to fused Pi/audio +5 V directly from distribution, not through the Pi header's output path. GND to star ground. Leave GAIN unconnected for the module default; start at low digital volume. Add 10 kohm from SD to GND so it starts disabled despite the module's weak pull-up.
- Speaker's two leads go only to the amplifier's two speaker terminals. Neither speaker terminal goes to ground; the amplifier output is bridged.
- PCA9685 VCC is 3.3 V logic; V+ is the separately fused 5 V motor branch. They are different nets. Use channel 0 for the servo: signal to yellow/orange, V+ to red, GND to brown/black, after checking the actual servo's labeling.
- Add **1 kohm from OE to 3.3 V**, retaining the board's existing 10 kohm pull-down. This holds OE near 3 V while GPIO22 is an input; driving GPIO22 LOW enables pulses. GPIO22 HIGH disables them. At LOW the pull-up draws about 3.3 mA. This is the opposite polarity/function of GPIO22 on the old custom PCB.
- Fit a 10 kohm pull-up from GPIO27 to 3.3 V. Wire the opposite switch contact to GND; check the internally paired legs of the four-leg tactile switch with a meter. Software debounce around 30 ms is a starting point.
- Fit 470–1000 uF / 10 V at PCA9685 V+ to GND with correct polarity and short leads, within the reserved diameter 8 x height 20 mm envelope. This reduces some transients; it is not a substitute for measurement.
- Keep I2S wires short, preferably below 100 mm, paired with nearby ground returns. Separate the motor/speaker wiring from microphone and I2S wiring.

## One-cable power

```text
Official Pi USB-C supply
  -> HUSB238 board, fixed 5 V / 3 A request
       + -> F1 2.5 A -> Pi 5 V inputs + amplifier VIN
       + -> F2 1.25 A -> removable MOTOR power link -> PCA9685 V+
       - -> star ground -> Pi, microphone, amplifier, PCA9685 and servo
```

On Adafruit 5807, **leave the 5V jumper closed**. Cut the factory 1A jumper and leave the 2A jumper open to request 3 A. Leave every higher-voltage jumper open. Do not connect the HUSB238 I2C pins to the Pi; fixed jumpers avoid software changing its output voltage. Inspect jumper continuity and measure unloaded output before connecting anything. Leaving all voltage jumpers open can request a damaging higher voltage.

Use 22 AWG stranded wire for power and ground branches with insulated soldered joints or properly rated connectors. A hand-wired isolated-pad perfboard or insulated harness can hold the two axial fuses; do not rely on thin perfboard copper tracks to carry combined load. Put fuses near the split and mechanically support the leads. A removable 2.54 mm power shunt rated at least 2 A provides the MOTOR link for bench isolation; mark its position clearly.

This arrangement powers the Pi through the header. **Do not simultaneously connect a powered cable to either Pi micro-USB socket.** Use network access for configuration. Any later USB peripheral/debug connection needs a deliberate backfeed-safe power arrangement.

Initial operating budget: Pi 0.75 A + amplifier 0.85 A + servo 0.80 A + other 0.05 A = 2.45 A. These are engineering allocations, not measured limits. No external USB loads are included. The 3 A request leaves 0.55 A nominal margin. A supply contract is not an active branch current limiter, and the fuses do not hold current to their nameplate values.

At 1.6 A the 2.5 A fuse's nominal cold resistance of 0.036 ohm contributes about 58 mV drop. At 0.8 A the 1.25 A motor fuse's 0.10 ohm contributes about 80 mV. Add wiring, PD-board MOSFET, connector and hot-fuse losses; these figures are not a worst-case power guarantee. Require measured stable voltage at the Pi and servo during the combined load test. Do not accept repeated Pi undervoltage events or servo-induced resets.

## Startup and shutdown

For first bring-up, keep the MOTOR link removed and the mechanical link detached. Set OE HIGH, initialize PCA9685 at 50 Hz and set channel 0 to a calibrated safe pulse before enabling OE. Keep all unused channels disabled. Establish the correct pulse direction and closed position before engaging the jaw mechanism.

The application must disable OE on errors and normal exit. On a program hang the PCA9685 can keep its last pulse running; there is no independent watchdog in this prototype. Do not present this as the old PCB's hardware fault latch. If the motor jams, remove motor power; a fuse may not open at stall current.

Never copy the old PCB's GPIO22 HIGH-to-arm code into this build: **HIGH means servo outputs OFF here**. GPIO25 supply-good and the old fault inputs do not exist. GPIO12 PWM overlay is unnecessary because the PCA9685 owns servo timing.
