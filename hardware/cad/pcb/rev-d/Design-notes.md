# Alfred revision D design notes

Pi Zero 2 W carrier; ICS-43434 I2S microphone; MAX98357A amplifier and enclosed 4-ohm/3-W speaker; one FS90 positional jaw servo. Four layers, 120 x 94 mm, nominal 1.6 mm FR-4, 35 um finished copper on every layer. Fixed mechanical interfaces retain revision B geometry. CAD-checked, unbuilt first article.

## Input power

Use the Raspberry Pi 27 W supply with its 5.1 V/5 A PD profile. CYPD3177 requests the selected 5 V/5 A contract. Its fallback switch output is unconnected, so an inadequate charger may leave the board off. A charger's headline wattage does not prove this profile. Never simultaneously power the Pi from its own connector and the carrier header.

Q1/Q2 are now **Vishay SI4459BDY-T1-GE3**, common-source back-to-back P-channel switches in the existing SO-8 footprint. Maximum on-resistance is 8.2 milliohms at -4.5 V and 25 C. At 4.1 A the pair contributes 0.06724 V drop and 0.276 W total dissipation at that specified point. Hot resistance and PCB/connector losses add to this. Verify gate voltage, startup timing and package temperatures.

R2 changes to 100k. Against the controller's maximum 3k pull-down plus R1=1k, the ideal resistor ratio gives 96.15% of source voltage as gate-source drive, before leakage. This shares an existing BOM value. D1 retains the 10 V gate clamp. Changed gate charge means PD-controlled startup/inrush must still be measured.

The conservative load allocation remains 4.1 A: Pi 2 A, amplifier 0.85 A, servo allowance 1.2 A and other circuitry 0.05 A. These are allocations, not measurements. Servo branch protection can deliberately shed an excessive load.

## Protected rails and corrected enable input

U2/U3 remain TPS259470LRPWR with reverse-current blocking and latch-off fault behavior. Their central footprint lands are IN/OUT, not ground. R101=1k gives about 3.334 A nominal Pi/audio current limit; R102=3.32k gives about 1.004 A nominal servo limit. Validate tolerances, startup and fault recovery with electronic loads.

The 34k/10k OVP dividers retain 5.28 V nominal cutoff, approximately 5.20-5.39 V including the specified threshold and resistor limits. OVP is a cutoff, not a 5 V regulator. Keep the amplifier within its operating voltage range.

**New EN protection:** R114=10k connects PD_5V to PI_EN_UVLO; R115=10k connects that node to ground. D101=MMSZ5V1T1G has cathode on PI_EN_UVLO, anode on ground. Normal EN voltage is about 2.55 V at 5.1 V input, comfortably above its approximately 1.2 V threshold.

Under a positive input fault, R114 limits current and D101 limits EN voltage. With an illustrative 28 V applied to this network alone, R114 current is below 2.8 mA and power below 80 mW; subtract the R115 current to obtain zener current. The diode's specified maximum is 5.36 V at 5 mA and 25 C, below EN's 6.5 V absolute maximum. Verify transient overshoot and temperature. This calculation does **not** authorize applying 28 V to the complete carrier or Pi; the other parts and USB protection impose separate limits.

C101/C102=4.7 nF give about 0.426 V/ms slew, a nominal 12 ms ramp. Charging C105=2200 uF requires about 0.94 A and C106=1000 uF about 0.43 A during this ramp, before active loads. Validate PD startup with the populated board.

## Precision supervisor and hardware arm latch

U4 is TPS389001DSET in a six-pad 1.5 x 1.5 mm WSON footprint. R107=32.1k 0.1% and R108=10k 0.1% monitor the protected Pi rail. RESET_N is SUPPLY_OK. R109 is now a 2.2k pullup to PI_3V3, not a feedback resistor. C109 bypasses U4. C111 is now a 100n delay capacitor; MR is tied high.

Nominal falling threshold: 1.15*(1+32.1/10) = **4.8415 V**. Nominal rising threshold: 1.157*(1+32.1/10) = **4.8710 V**. Including +/-1% supervisor thresholds, resistor tolerances and a conservative +/-100 nA sense-current term gives **4.783-4.901 V falling** and **4.812-4.930 V rising**. These are static bounds at the sensing point. Delay, trace/contact drop to the Pi and reservoir ESR still matter; this does not guarantee 4.75 V at the Pi header during all transients.

C111 gives about **107 ms nominal** reset-release qualification. It holds SUPPLY_OK low until the rail remains healthy; it does not delay initial detection by 107 ms. TPS3890 specifies an 18 us typical detection delay at 3.3 V with 5% overdrive, not a guaranteed maximum for small overdrive. Timing and capacitor tolerances change the recovery interval.

U11 is **Nexperia 74AUP1G74DC,125**, powered from PI_3V3 and bypassed by C112. D (pin 2) and active-low set (pin 7) are high. Active-low reset (pin 6) is SUPPLY_OK. Clock (pin 1) receives SERVO_REQUEST. Q (pin 5) is SERVO_ARMED; complement Q (pin 3) is unconnected. U5 ANDs SERVO_ARMED with SERVO_REQUEST to drive the servo eFuse.

A detected supply fault asynchronously clears the latch. Recovery with request held high leaves the servo OFF. A fresh low-to-high request after supply-good qualification is required to re-arm. Request low always disables power through U5. Software must not automatically pulse request repeatedly after a fault. The supervisor power-on reset initializes the latch; verify actual Pi_3V3 startup/shutdown ramps.

Use the specified AUP part. Its Schmitt inputs permit 200 ns/V transitions; the initial LVC candidate permits only 10 ns/V. R109=2.2k limits reset-release RC rise time. At an illustrative total SUPPLY_OK load of 100 pF, 2.2RC/(0.8*3.3) is about 183 ns/V. Measure at U11 pin 6 and require <=200 ns/V; do not attach long external leads. Do not substitute the LVC candidate without edge conditioning.

At 25 C, using PMOS maximum 8.2 milliohms each and eFuse typical 28.3 milliohms, the earlier allocation gives about 4.973 V with 2.85 A Pi/audio and servo off, or 4.952 V with 4.1 A total. Margin to the upper calculated threshold is about 42 mV before enabling and 51 mV while running, before additional losses. These mixed maximum/typical values are not a complete hot/cable/contact worst-case guarantee. Nominal-threshold margins are larger. The earlier nominal conflict is removed and faults latch off; excessive total voltage drop still disables the jaw.

Bench acceptance: measure at the Pi pins and R107 feed with the specified supply, Wi-Fi/audio and supervised servo load. Require intended jaw availability, >=4.75 V at the Pi header, and no restart after a detected fault until a deliberate command edge. If this fails, revisit the complete power path and measured load; do not lower R107 blindly. The reservoir cannot bridge arbitrary source collapse.

## Audio

**Do not fit R304.** Floating GAIN_SLOT selects 9 dB. The datasheet full-scale reference plus gain is 2.1+9=11.1 dBV, or 3.589 Vrms, mathematically 3.221 W into 4 ohms before rail limitation/filter loss. This removes the previous approximately 0.81 W gain limit, but does not promise clean 3 W speech output. Use software attenuation and start quietly. The optional 100k R304 can be fitted for a quieter 3 dB variant.

All other amplifier decoupling/filter parts remain fitted. Neither speaker lead is ground. Do not connect an earth-referenced oscilloscope ground to either speaker terminal. L1/L2 remain 10 uH each, C306=220 nF differential, C307/C308=1 nF to ground; ideal differential resonance is about 75.9 kHz. Validate response/EMI with real wiring.

Pi drives BCLK/LRCLK; microphone and amplifier use separate data wires. Use standard I2S, 48 kHz, two 32-bit slots and 3.072 MHz BCLK. Capture and playback use the left slot. R301=47 ohms filters microphone supply with local capacitors. Keep the bottom acoustic bore free of solder, flux and cleaning liquid.

The `software/` directory supplies an overlay using the Raspberry Pi voiceHAT interface drivers, changed to Alfred's GPIO17 amplifier enable. Source review supports the intended duplex format/clock arrangement. Target compilation, boot and actual streaming remain untested. Echo cancellation requires a separate playback-reference acoustic/software solution.

## Jaw, button and LED

GPIO12 hardware PWM feeds the SN74LVC1G07 buffer; R402 pulls up from the switched servo rail and R403 limits signal fault current. GPIO22 requests power, GPIO25 reads supply-good, GPIO27 reads active-low servo fault. Keep the request low by default. Do not use PCM-based servo timing while audio uses I2S. The unkeyed servo header is GND/+5 V/signal. Calibrate jaw endpoints with the linkage detached first.

The existing TL431/Q3/10-ohm dump circuit remains. Its ideal threshold is about 5.589 V; reference current, tolerance and dynamics change this. At 5.6 V the dump resistor draws about 0.56 A and dissipates 3.14 W when fully on. Validate regeneration pulses, loop stability, overshoot and enclosed temperatures. Keep the raised 5 W resistor clear of plastic/wiring as specified in assembly instructions.

The button retains RC filtering and a Schmitt buffer. Require at least 30 ms stable-state software debounce on both edges. GPIO24 drives the green LED through 680 ohms.

## Release and sources

Follow `Fabrication-and-assembly.md`: measure PD negotiation, startup, EN voltage, current limiting, OVP, supply-good trip points, Pi-header droop, regeneration and component temperature, then test 30 minutes of simultaneous audio under Wi-Fi/jaw load. Preserve the antenna keepout. CAD results do not prove these behaviors. Purchasing estimates are in `Cost-and-purchasing.md`.

- [Si4459BDY](https://www.vishay.com/docs/76759/si4459bdy.pdf)
- [MMSZ5V1T1G series](https://www.onsemi.com/pdf/datasheet/mmsz2v4t1-d.pdf)
- [TPS25947](https://www.ti.com/lit/ds/symlink/tps25947.pdf)
- [TPS3890](https://www.ti.com/lit/ds/symlink/tps3890.pdf)
- [Nexperia 74AUP1G74](https://assets.nexperia.com/documents/data-sheet/74AUP1G74.pdf)
- [CYPD3177](https://www.infineon.com/assets/row/public/documents/24/49/infineon-cypd3177-24lqxq-datasheet-en.pdf)
- [MAX98357A](https://www.analog.com/media/en/technical-documentation/data-sheets/MAX98357A-MAX98357B.pdf)
- [Audio integration sources and target setup](software/README.md)
