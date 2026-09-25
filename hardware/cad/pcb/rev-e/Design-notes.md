# Alfred revision E design notes

Pi Zero 2 W carrier; ICS-43434 I2S microphone; MAX98357A amplifier and enclosed 4-ohm/3-W speaker; one FS90 positional jaw servo. Four layers, 120 x 94 mm, nominal 1.6 mm FR-4, 35 um finished copper on every layer. Fixed mechanical interfaces retain revision B geometry. CAD-checked, unbuilt first article.

## Input power

Use the Raspberry Pi 27 W supply with its 5.1 V/5 A PD profile. CYPD3177 requests the selected 5 V/5 A contract. Its fallback switch output is unconnected, so an inadequate charger may leave the board off. A charger's headline wattage does not prove this profile. Never simultaneously power the Pi from its own connector and the carrier header.

Q1/Q2 are now **Vishay SI4459BDY-T1-GE3**, common-source back-to-back P-channel switches in the existing SO-8 footprint. Maximum on-resistance is 8.2 milliohms at -4.5 V and 25 C. At 4.1 A the pair contributes 0.06724 V drop and 0.276 W total dissipation at that specified point. Hot resistance and PCB/connector losses add to this. Verify gate voltage, startup timing and package temperatures.

R2 changes to 100k. Against the controller's maximum 3k pull-down plus R1=1k, the ideal resistor ratio gives 96.15% of source voltage as gate-source drive, before leakage. This shares an existing BOM value. D1 retains the 10 V gate clamp. Changed gate charge means PD-controlled startup/inrush must still be measured.

Revision E is scoped to the bare Pi Zero 2 W, onboard audio and one FS90. The design target is <=1.65 A on PI_5V (0.75 A Pi allocation, 0.85 A amplifier allocation, 0.05 A other) and <=0.80 A on the powered servo branch, 2.45 A combined. These are acceptance limits, not measured consumption. External USB loads, other Pi models and a sustained servo stall are outside this envelope. The previous 4.1 A allocation is withdrawn: it was not a validated operating capability.

## Protected rails and corrected enable input

U2/U3 remain TPS259470LRPWR with reverse-current blocking and latch-off fault behavior. Their central footprint lands are IN/OUT, not ground. R101=1.65k 0.1% gives about 2.02 A nominal Pi/audio current limit; R102=3.32k gives about 1.004 A nominal servo limit. Validate tolerances, startup and fault recovery with electronic loads.

The 34k/10k OVP dividers retain 5.28 V nominal cutoff, approximately 5.20-5.39 V including the specified threshold and resistor limits. OVP is a cutoff, not a 5 V regulator. Keep the amplifier within its operating voltage range.

**New EN protection:** R114=10k connects PD_5V to PI_EN_UVLO; R115=10k connects that node to ground. D101=MMSZ5V1T1G has cathode on PI_EN_UVLO, anode on ground. Normal EN voltage is about 2.55 V at 5.1 V input, comfortably above its approximately 1.2 V threshold.

Under a positive input fault, R114 limits current and D101 limits EN voltage. With an illustrative 28 V applied to this network alone, R114 current is below 2.8 mA and power below 80 mW; subtract the R115 current to obtain zener current. The diode's specified maximum is 5.36 V at 5 mA and 25 C, below EN's 6.5 V absolute maximum. Verify transient overshoot and temperature. This calculation does **not** authorize applying 28 V to the complete carrier or Pi; the other parts and USB protection impose separate limits.

C101 is now 10 nF C0G, 5%; C102 remains 4.7 nF. The Pi/audio ramp is about 0.20 V/ms (25.5 ms to 5.1 V); its 2200 uF reservoir draws about 0.44 A nominal during charging. The servo ramp remains about 0.426 V/ms (12 ms) and 0.43 A nominal reservoir charging current. Keep the amplifier and servo disabled during Pi startup. A screening estimate using +20% bulk capacitance, -5% timing capacitance and the 3.82/2.21 maximum/typical dVdt charging-current ratio gives about 0.96 A Pi reservoir inrush; adding the 0.75 A Pi allocation gives 1.71 A. This is below the 1.8 A minimum listed overcurrent threshold at 1.65k, but is not a guaranteed slew-rate bound: measure real startup, internal transfer variation and Pi boot current. The divider's 0.1% resistance tolerance makes the approximate current-threshold range 1.798-2.202 A. Overcurrent limiting is not instantaneous and may terminate in thermal latch-off.

## Precision supervisor and hardware arm latch

U4 is TPS389001DSET in a six-pad 1.5 x 1.5 mm WSON footprint. R107=32.0k 0.1% and R108=10k 0.1% monitor the protected Pi rail. RESET_N is SUPPLY_OK. R109 is now a 2.2k pullup to PI_3V3, not a feedback resistor. C109 bypasses U4. C111 is now a 100n delay capacitor; MR is tied high.

Nominal falling threshold: 1.15*(1+32.0/10) = **4.8300 V**. Nominal rising threshold: 1.157*(1+32.0/10) = **4.8594 V**. Including +/-1% supervisor thresholds, resistor tolerances and a conservative +/-100 nA sense-current term gives **4.771-4.889 V falling** and **4.800-4.919 V rising**. These are static bounds at the sensing point. Delay, trace/contact drop to the Pi and reservoir ESR still matter; this does not guarantee 4.75 V at the Pi header during all transients.

C111 gives about **107 ms nominal** reset-release qualification. It holds SUPPLY_OK low until the rail remains healthy; it does not delay initial detection by 107 ms. TPS3890 specifies an 18 us typical detection delay at 3.3 V with 5% overdrive, not a guaranteed maximum for small overdrive. Timing and capacitor tolerances change the recovery interval.

U11 is **Nexperia 74AUP1G74DC,125**, powered from PI_3V3 and bypassed by C112. D (pin 2) and active-low set (pin 7) are high. Active-low reset (pin 6) is SUPPLY_OK. Clock (pin 1) receives SERVO_REQUEST. Q (pin 5) is SERVO_ARMED; complement Q (pin 3) is unconnected. U5 ANDs SERVO_ARMED with SERVO_REQUEST to drive the servo eFuse.

A detected supply fault asynchronously clears the latch. Recovery with request held high leaves the servo OFF. A fresh low-to-high request after supply-good qualification is required to re-arm. Request low always disables power through U5. Software must not automatically pulse request repeatedly after a fault. The supervisor power-on reset initializes the latch; verify actual Pi_3V3 startup/shutdown ramps.

Use the specified AUP part. Its Schmitt inputs permit 200 ns/V transitions; the initial LVC candidate permits only 10 ns/V. R109=2.2k limits reset-release RC rise time. At an illustrative total SUPPLY_OK load of 100 pF, 2.2RC/(0.8*3.3) is about 183 ns/V. Measure at U11 pin 6 and require <=200 ns/V; do not attach long external leads. Do not substitute the LVC candidate without edge conditioning.

R107 is the catalogued Yageo RT0805BRD0732KL; the earlier 32.1k MPN was not verified and is removed. Threshold values above include initial resistor tolerances. The 25 ppm/C resistor temperature coefficients also matter: the validation script separately evaluates opposing drift up to 100 C from the 25 C reference. This widens the bounds and reduces the lowest cutoff margin. Neither static bounds nor this supervisor can guarantee no transient below 4.75 V.

At the new acceptance loads and 5.1 V input, the same 25 C mixed maximum/typical model used for revision D gives PI_5V about 5.026 V before servo enable and 5.013 V while running. Against the initial-tolerance upper thresholds, the margins are about 108 mV and 124 mV. Much of this improvement comes from the smaller supported load, not from the resistor change. R101 now enforces a lower overload threshold; it does not regulate normal load current or guarantee a hard 2.02 A ceiling during transients.

Use `Power-acceptance.md` and `software/validate-hardware-logic.py` for the stronger sensitivity calculation: 45 milliohm eFuse maximum, a stated 1.5x engineering allowance on MOSFET resistance, resistor temperature drift and 20 mV additional PCB/header loss. The MOSFET hot factor and the PCB loss allowance must be measured; they are not manufacturer guarantees. Minimum voltage is specified at the input connector pads, so upstream cable/contact loss must be accounted for separately. This turns the earlier vague power claim into a constrained build target; it does not prove the specified supply meets it.

Bench acceptance remains required. If input voltage or measured path loss fails the envelope, the power-path problem is not closed: qualify a lower supported load or redesign the power conversion/path. Do not bypass protection or lower R107 further to hide a failed load test.

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

Changed passive specifications: [R107 catalog entry](https://www.digikey.com/en/products/detail/yageo/RT0805BRD0732KL/17024521), [R101 catalog entry](https://www.digikey.com/en/products/detail/yageo/RT0805BRD071K65L/1075688), [C101 manufacturer specification](https://yageogroup.com/download/specsheet/C0805C103J5GACTU). These links establish component identity; purchasing is deferred.
