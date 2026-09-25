# Alfred revision D component ledger

The native schematic and PCB are authoritative. R304 is intentionally not fitted.

## J1 - USB-C 5V/5A PD
MPN: USB4105-GF-A. Footprint: Connector_USB:USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal.
Power-only input; integrated Rd in U1. All VBUS contacts connected.
Pins: A1=GND, A12=GND, B1=GND, B12=GND, SH=GND, A4=VBUS, A9=VBUS, B4=VBUS, B9=VBUS, A5=CC1, B5=CC2, A6=NC, A7=NC, A8=NC, B6=NC, B7=NC, B8=NC

## U1 - CYPD3177-24LQXQ
MPN: CYPD3177-24LQXQ. Footprint: Package_DFN_QFN:QFN-24-1EP_4x4mm_P0.5mm_EP2.75x2.75mm.
5 V min=max; coarse 5 A; fine 0 A. Standalone, no NVM programming.
Pins: 1=GND, 2=GND, 3=PD_GATE_DRV, 4=NC, 5=PD_3V3, 6=GND, 7=NC, 8=NC, 9=PD_FAULT, 10=PD_FLIP, 11=PD_5V, 12=NC, 13=NC, 14=CC2, 15=CC1, 16=NC, 17=NC, 18=VBUS, 19=GND, 20=NC, 21=NC, 22=GND, 23=PD_3V3, 24=PD_1V8, 25=GND

## Q1 - Si4459BDY
MPN: SI4459BDY-T1-GE3. Footprint: Package_SO:SO-8_3.9x4.9mm_P1.27mm.
30V SO8 PMOS; max 8.2 milliohm at VGS=-4.5V, 25C; lower input path drop than rev C.
Pins: 1=PFET_SOURCE, 2=PFET_SOURCE, 3=PFET_SOURCE, 4=PFET_GATE, 5=VBUS, 6=VBUS, 7=VBUS, 8=VBUS

## Q2 - Si4459BDY
MPN: SI4459BDY-T1-GE3. Footprint: Package_SO:SO-8_3.9x4.9mm_P1.27mm.
30V SO8 PMOS; max 8.2 milliohm at VGS=-4.5V, 25C; lower input path drop than rev C.
Pins: 1=PFET_SOURCE, 2=PFET_SOURCE, 3=PFET_SOURCE, 4=PFET_GATE, 5=PD_5V, 6=PD_5V, 7=PD_5V, 8=PD_5V

## R1 - 1k 1%
MPN: RC0805FR-071KL. Footprint: Resistor_SMD:R_0805_2012Metric.
Gate-driver isolation.
Pins: 1=PD_GATE_DRV, 2=PFET_GATE

## R2 - 100k 1%
MPN: RC0805FR-07100KL. Footprint: Resistor_SMD:R_0805_2012Metric.
Default gates off; 100k reduces loss of gate drive against driver pull-down resistance and shares an existing BOM value.
Pins: 1=PFET_SOURCE, 2=PFET_GATE

## R3 - 49.9k 1%
MPN: RC0805FR-0749K9L. Footprint: Resistor_SMD:R_0805_2012Metric.
Advertise no USB data capability; 49.9k nominal 50k.
Pins: 1=PD_3V3, 2=PD_FLIP

## R4 - 10k 1%
MPN: RC0805FR-0710KL. Footprint: Resistor_SMD:R_0805_2012Metric.
Input discharge/bleeder as reference design.
Pins: 1=VBUS, 2=GND

## D1 - 10V gate zener
MPN: BZT52C10-7-F. Footprint: Diode_SMD:D_SOD-123.
Limits magnitude of PMOS gate-source voltage.
Pins: 1=PFET_SOURCE, 2=PFET_GATE

## D2 - 15V transient suppressor
MPN: SMAJ15A-13-F. Footprint: Diode_SMD:D_SMA.
24.4 V maximum rated pulse clamp, below 28 V eFuse absolute maximum; not a sustained overvoltage absorber.
Pins: 1=VBUS, 2=GND

## C1 - 1u
MPN: C0805C105K5RACTU. Footprint: Capacitor_SMD:C_0805_2012Metric.
Input capacitance before controlled switch, 50 V.
Pins: 1=VBUS, 2=GND

## C2 - 1u
MPN: C0805C105K5RACTU. Footprint: Capacitor_SMD:C_0805_2012Metric.
Local decoupling; X7R unless noted.
Pins: 1=PD_3V3, 2=GND

## C3 - 100n
MPN: C0805C104K5RACTU. Footprint: Capacitor_SMD:C_0805_2012Metric.
Local decoupling; X7R unless noted.
Pins: 1=PD_3V3, 2=GND

## C4 - 100n
MPN: C0805C104K5RACTU. Footprint: Capacitor_SMD:C_0805_2012Metric.
Local decoupling; X7R unless noted.
Pins: 1=PD_3V3, 2=GND

## C5 - 1u
MPN: C0805C105K5RACTU. Footprint: Capacitor_SMD:C_0805_2012Metric.
Local decoupling; X7R unless noted.
Pins: 1=PD_1V8, 2=GND

## C6 - 1u
MPN: C0805C105K5RACTU. Footprint: Capacitor_SMD:C_0805_2012Metric.
Decoupling after PD FETs.
Pins: 1=PD_5V, 2=GND

## TP1 - VBUS
MPN: PCB copper test point. Footprint: TestPoint:TestPoint_Pad_D1.5mm.
Probe access; no purchased component
Pins: 1=VBUS

## TP2 - PD_5V
MPN: PCB copper test point. Footprint: TestPoint:TestPoint_Pad_D1.5mm.
Probe access; no purchased component
Pins: 1=PD_5V

## TP3 - PD_FAULT
MPN: PCB copper test point. Footprint: TestPoint:TestPoint_Pad_D1.5mm.
Probe access; no purchased component
Pins: 1=PD_FAULT

## TP4 - GND
MPN: PCB copper test point. Footprint: TestPoint:TestPoint_Pad_D1.5mm.
Probe access; no purchased component
Pins: 1=GND

## TP5 - PD_3V3
MPN: PCB copper test point. Footprint: TestPoint:TestPoint_Pad_D1.5mm.
Probe access; no purchased component
Pins: 1=PD_3V3

## TP6 - PD_1V8
MPN: PCB copper test point. Footprint: TestPoint:TestPoint_Pad_D1.5mm.
Probe access; no purchased component
Pins: 1=PD_1V8

## U2 - TPS259470LRPWR
MPN: TPS259470LRPWR. Footprint: Alfred:TI_RPW0010A.
Adjustable OVP, active current limit, thermal latch-off and reverse blocking; ITIMER open.
Pins: 1=PI_EN_UVLO, 2=PI_OV, 3=NC, 4=PI_FAULT_N, 5=PD_5V, 6=PI_5V, 7=PI_DVDT, 8=GND, 9=PI_ILM, 10=NC

## U3 - TPS259470LRPWR
MPN: TPS259470LRPWR. Footprint: Alfred:TI_RPW0010A.
Adjustable OVP, active current limit, thermal latch-off and reverse blocking; ITIMER open.
Pins: 1=SERVO_EN, 2=SERVO_OV, 3=NC, 4=SERVO_FAULT_N, 5=PD_5V, 6=SERVO_5V, 7=SERVO_DVDT, 8=GND, 9=SERVO_ILM, 10=NC

## R101 - 1k 0.1%
MPN: RT0805BRD071KL. Footprint: Resistor_SMD:R_0805_2012Metric.
3334/1000 = 3.334 A nominal limit; about 3.0 A minimum, Pi plus amp.
Pins: 1=PI_ILM, 2=GND

## R102 - 3.32k 0.1%
MPN: RT0805BRD073K32L. Footprint: Resistor_SMD:R_0805_2012Metric.
3334/3320 = 1.004 A nominal; approx 0.85-1.15 A tolerance band.
Pins: 1=SERVO_ILM, 2=GND

## R103 - 34.0k 0.1%
MPN: RT0805BRD0734KL. Footprint: Resistor_SMD:R_0805_2012Metric.
1.2*(1+34/10)=5.28 V nominal overvoltage cutoff.
Pins: 1=PD_5V, 2=PI_OV

## R104 - 10k 0.1%
MPN: RT0805BRD0710KL. Footprint: Resistor_SMD:R_0805_2012Metric.
Precision OVP divider bottom.
Pins: 1=PI_OV, 2=GND

## R105 - 34.0k 0.1%
MPN: RT0805BRD0734KL. Footprint: Resistor_SMD:R_0805_2012Metric.
1.2*(1+34/10)=5.28 V nominal overvoltage cutoff.
Pins: 1=PD_5V, 2=SERVO_OV

## R106 - 10k 0.1%
MPN: RT0805BRD0710KL. Footprint: Resistor_SMD:R_0805_2012Metric.
Precision OVP divider bottom.
Pins: 1=SERVO_OV, 2=GND

## C101 - 4.7n
MPN: C0805C472J5GACTU. Footprint: Capacitor_SMD:C_0805_2012Metric.
0.426 V/ms nominal slew; about 12 ms ramp. C0G.
Pins: 1=PI_DVDT, 2=GND

## C102 - 4.7n
MPN: C0805C472J5GACTU. Footprint: Capacitor_SMD:C_0805_2012Metric.
0.426 V/ms nominal slew; about 0.43 A capacitor charging current.
Pins: 1=SERVO_DVDT, 2=GND

## C103 - 100n
MPN: C0805C104K5RACTU. Footprint: Capacitor_SMD:C_0805_2012Metric.
U2 input bypass.
Pins: 1=PD_5V, 2=GND

## C104 - 100n
MPN: C0805C104K5RACTU. Footprint: Capacitor_SMD:C_0805_2012Metric.
U3 input bypass.
Pins: 1=PD_5V, 2=GND

## C105 - 2200u 10V
MPN: EEU-FR1A222L. Footprint: Capacitor_THT:CP_Radial_D10.0mm_P5.00mm.
Reverse-isolated Pi/audio reservoir; +/-20%; hand-solder after reflow.
Pins: 1=PI_5V, 2=GND

## C106 - 1000u 10V
MPN: EEU-FR1A102L. Footprint: Capacitor_THT:CP_Radial_D8.0mm_P3.50mm.
Servo reservoir; +/-20%; hand-solder after reflow.
Pins: 1=SERVO_5V, 2=GND

## C107 - 10u
MPN: C1206C106K4RACTU. Footprint: Capacitor_SMD:C_1206_3216Metric.
Local decoupling; X7R unless noted.
Pins: 1=PI_5V, 2=GND

## C108 - 10u
MPN: C1206C106K4RACTU. Footprint: Capacitor_SMD:C_1206_3216Metric.
Local decoupling; X7R unless noted.
Pins: 1=SERVO_5V, 2=GND

## U4 - TPS389001DSET
MPN: TPS389001DSET. Footprint: Package_SON:WSON-6_1.5x1.5mm_P0.5mm.
1% supervisor; nominal 4.842V trip, about 107ms good-rail recovery qualification; asynchronous latch clear.
Pins: 1=UV_SENSE, 2=GND, 3=PI_3V3, 4=PI_3V3, 5=UV_DELAY, 6=SUPPLY_OK

## R107 - 32.1k 0.1%
MPN: RT0805BRD0732K1L. Footprint: Resistor_SMD:R_0805_2012Metric.
Supervisor divider top, nominal falling threshold 1.15*(1+32.1/10)=4.8415V.
Pins: 1=PI_5V, 2=UV_SENSE

## R108 - 10k 0.1%
MPN: RT0805BRD0710KL. Footprint: Resistor_SMD:R_0805_2012Metric.
UV threshold divider bottom.
Pins: 1=UV_SENSE, 2=GND

## R109 - 2.2k 1%
MPN: RC0805FR-072K2L. Footprint: Resistor_SMD:R_0805_2012Metric.
Supervisor open-drain pullup; 1.5mA sink at3.3V, faster reset-release edge for AUP latch.
Pins: 1=SUPPLY_OK, 2=PI_3V3

## C109 - 100n
MPN: C0805C104K5RACTU. Footprint: Capacitor_SMD:C_0805_2012Metric.
Supervisor supply bypass.
Pins: 1=PI_3V3, 2=GND

## U5 - SN74LVC1G08DBVR
MPN: SN74LVC1G08DBVR. Footprint: Package_TO_SOT_SMD:SOT-23-5.
AND of hardware armed latch and software request; request low always disables power.
Pins: 1=SERVO_ARMED, 2=SERVO_REQUEST, 3=GND, 4=SERVO_EN, 5=PI_3V3

## R110 - 100k 1%
MPN: RC0805FR-07100KL. Footprint: Resistor_SMD:R_0805_2012Metric.
Keep motor supply off with Pi absent.
Pins: 1=SERVO_EN, 2=GND

## R111 - 100k 1%
MPN: RC0805FR-07100KL. Footprint: Resistor_SMD:R_0805_2012Metric.
Default off during boot.
Pins: 1=SERVO_REQUEST, 2=GND

## R112 - 10k 1%
MPN: RC0805FR-0710KL. Footprint: Resistor_SMD:R_0805_2012Metric.
Fault output pull-up.
Pins: 1=PI_3V3, 2=SERVO_FAULT_N

## R113 - 10k 1%
MPN: RC0805FR-0710KL. Footprint: Resistor_SMD:R_0805_2012Metric.
Fault output pull-up.
Pins: 1=PI_3V3, 2=PI_FAULT_N

## C110 - 100n
MPN: C0805C104K5RACTU. Footprint: Capacitor_SMD:C_0805_2012Metric.
AND gate bypass.
Pins: 1=PI_3V3, 2=GND

## C111 - 100n
MPN: C0805C104K5RACTU. Footprint: Capacitor_SMD:C_0805_2012Metric.
Supervisor reset-release delay about107ms nominal; delay qualification only, not fault detection delay.
Pins: 1=UV_DELAY, 2=GND

## TP101 - PI_5V
MPN: PCB copper test point. Footprint: TestPoint:TestPoint_Pad_D1.5mm.
Probe access; no purchased component
Pins: 1=PI_5V

## TP102 - SERVO_5V
MPN: PCB copper test point. Footprint: TestPoint:TestPoint_Pad_D1.5mm.
Probe access; no purchased component
Pins: 1=SERVO_5V

## TP103 - SUPPLY_OK
MPN: PCB copper test point. Footprint: TestPoint:TestPoint_Pad_D1.5mm.
Probe access; no purchased component
Pins: 1=SUPPLY_OK

## TP104 - SERVO_ILM
MPN: PCB copper test point. Footprint: TestPoint:TestPoint_Pad_D1.5mm.
Probe access; no purchased component
Pins: 1=SERVO_ILM

## TP105 - PI_FAULT_N
MPN: PCB copper test point. Footprint: TestPoint:TestPoint_Pad_D1.5mm.
Probe access; no purchased component
Pins: 1=PI_FAULT_N

## TP106 - GND
MPN: PCB copper test point. Footprint: TestPoint:TestPoint_Pad_D1.5mm.
Probe access; no purchased component
Pins: 1=GND

## J2 - Pi Zero 2 W carrier socket
MPN: SSW-120-01-G-D. Footprint: Connector_PinSocket_2.54mm:PinSocket_2x20_P2.54mm_Vertical.
Socket on carrier top; male header soldered on Pi underside; all grounds and both 5V pins used.
Pins: 1=PI_3V3, 2=PI_5V, 4=PI_5V, 11=AMP_ENABLE, 12=BCLK_PI, 13=SERVO_FAULT_N, 15=SERVO_REQUEST, 16=BUTTON_N, 18=LED_GPIO, 22=SUPPLY_OK, 32=JAW_PWM, 35=LRCLK_PI, 38=MIC_DATA_PI, 40=AMP_DATA_PI, 6=GND, 9=GND, 14=GND, 20=GND, 25=GND, 30=GND, 34=GND, 39=GND, 3=NC, 5=NC, 7=NC, 8=NC, 10=NC, 17=NC, 19=NC, 21=NC, 23=NC, 24=NC, 26=NC, 27=NC, 28=NC, 29=NC, 31=NC, 33=NC, 36=NC, 37=NC

## R201 - 33 1%
MPN: RC0805FR-0733RL. Footprint: Resistor_SMD:R_0805_2012Metric.
Source damping at Pi, shared clock.
Pins: 1=BCLK_PI, 2=BCLK

## R202 - 33 1%
MPN: RC0805FR-0733RL. Footprint: Resistor_SMD:R_0805_2012Metric.
Source damping at Pi, shared frame clock.
Pins: 1=LRCLK_PI, 2=LRCLK

## R203 - 33 1%
MPN: RC0805FR-0733RL. Footprint: Resistor_SMD:R_0805_2012Metric.
Source damping at Pi.
Pins: 1=AMP_DATA_PI, 2=AMP_DATA

## TP201 - PI_3V3
MPN: PCB copper test point. Footprint: TestPoint:TestPoint_Pad_D1.5mm.
Probe access; no purchased component
Pins: 1=PI_3V3

## TP202 - BCLK
MPN: PCB copper test point. Footprint: TestPoint:TestPoint_Pad_D1.5mm.
Probe access; no purchased component
Pins: 1=BCLK

## TP203 - LRCLK
MPN: PCB copper test point. Footprint: TestPoint:TestPoint_Pad_D1.5mm.
Probe access; no purchased component
Pins: 1=LRCLK

## TP204 - MIC_DATA_PI
MPN: PCB copper test point. Footprint: TestPoint:TestPoint_Pad_D1.5mm.
Probe access; no purchased component
Pins: 1=MIC_DATA_PI

## TP205 - GND
MPN: PCB copper test point. Footprint: TestPoint:TestPoint_Pad_D1.5mm.
Probe access; no purchased component
Pins: 1=GND

## U6 - ICS-43434
MPN: ICS-43434. Footprint: Sensor_Audio:InvenSense_ICS-43434-6_3.5x2.65mm.
Left slot selected. Bottom port through PCB; no paste/flux in port.
Pins: 1=LRCLK, 2=GND, 3=GND, 4=BCLK, 5=MIC_3V3, 6=MIC_DATA

## R301 - 47 1%
MPN: RC0805FR-0747RL. Footprint: Resistor_SMD:R_0805_2012Metric.
Quiet local mic supply; 550uA produces only 25.9mV drop.
Pins: 1=PI_3V3, 2=MIC_3V3

## C301 - 1u
MPN: C0805C105K5RACTU. Footprint: Capacitor_SMD:C_0805_2012Metric.
Mic RC supply filter.
Pins: 1=MIC_3V3, 2=GND

## C302 - 100n
MPN: C0805C104K5RACTU. Footprint: Capacitor_SMD:C_0805_2012Metric.
Mic immediate bypass.
Pins: 1=MIC_3V3, 2=GND

## R302 - 33 1%
MPN: RC0805FR-0733RL. Footprint: Resistor_SMD:R_0805_2012Metric.
Source termination at microphone.
Pins: 1=MIC_DATA, 2=MIC_DATA_PI

## R303 - 100k 1%
MPN: RC0805FR-07100KL. Footprint: Resistor_SMD:R_0805_2012Metric.
Defined data level during microphone tri-state slot.
Pins: 1=MIC_DATA_PI, 2=GND

## U7 - MAX98357AETE+T
MPN: MAX98357AETE+T. Footprint: Package_DFN_QFN:TQFN-16-1EP_3x3mm_P0.5mm_EP1.23x1.23mm.
Mono bridge amplifier; A=I2S; EP grounded; both speaker leads driven.
Pins: 1=AMP_DATA, 2=AMP_GAIN, 3=GND, 4=AMP_SD, 5=NC, 6=NC, 7=PI_5V, 8=PI_5V, 9=AMP_P, 10=AMP_N, 11=GND, 12=NC, 13=NC, 14=LRCLK, 15=GND, 16=BCLK, 17=GND

## R304 - 100k 1%
MPN: RC0805FR-07100KL. Footprint: Alfred:R_0805_DNP_NoPaste.
DO NOT FIT in revision D: floating GAIN_SLOT selects 9 dB. Optional 100k to VDD selects quiet 3 dB mode.
Pins: 1=AMP_GAIN, 2=PI_5V

## R305 - 1k 1%
MPN: RC0805FR-071KL. Footprint: Resistor_SMD:R_0805_2012Metric.
SD_MODE drive isolation; high selects left channel.
Pins: 1=AMP_ENABLE, 2=AMP_SD

## R306 - 100k 1%
MPN: RC0805FR-07100KL. Footprint: Resistor_SMD:R_0805_2012Metric.
Mute through boot; software enables after valid clocks.
Pins: 1=AMP_SD, 2=GND

## C303 - 100n
MPN: C0805C104K5RACTU. Footprint: Capacitor_SMD:C_0805_2012Metric.
At amplifier supply pins.
Pins: 1=PI_5V, 2=GND

## C304 - 10u
MPN: C1206C106K4RACTU. Footprint: Capacitor_SMD:C_1206_3216Metric.
At amplifier supply pins.
Pins: 1=PI_5V, 2=GND

## C305 - 100u 10V
MPN: EEU-FR1A101. Footprint: Capacitor_THT:CP_Radial_D5.0mm_P2.00mm.
Local amplifier bulk.
Pins: 1=PI_5V, 2=GND

## L1 - 10uH 3.2A
MPN: SRN6045TA-100M. Footprint: Alfred:SRN6045TA_100M.
Symmetric output LC; 4.6A saturation, DCR 52mOhm maximum; 6x6mm body.
Pins: 1=AMP_P, 2=SPK_P

## L2 - 10uH 3.2A
MPN: SRN6045TA-100M. Footprint: Alfred:SRN6045TA_100M.
Symmetric output LC; 4.6A saturation, DCR 52mOhm maximum; 6x6mm body.
Pins: 1=AMP_N, 2=SPK_N

## C306 - 220n
MPN: C0805C224K5RACTU. Footprint: Capacitor_SMD:C_0805_2012Metric.
Differential output filter; 20uH total gives 75.9kHz resonance.
Pins: 1=SPK_P, 2=SPK_N

## C307 - 1n
MPN: C0805C102J5GACTU. Footprint: Capacitor_SMD:C_0805_2012Metric.
C0G 50V, post-inductor common-mode EMI shunt.
Pins: 1=SPK_P, 2=GND

## C308 - 1n
MPN: C0805C102J5GACTU. Footprint: Capacitor_SMD:C_0805_2012Metric.
Matched C0G 50V, post-inductor EMI shunt.
Pins: 1=SPK_N, 2=GND

## J3 - Speaker 4ohm 3W
MPN: 282834-2. Footprint: TerminalBlock_TE-Connectivity:TerminalBlock_TE_282834-2_1x02_P2.54mm_Horizontal.
Screw terminal for bare speaker wires; neither terminal is ground.
Pins: 1=SPK_P, 2=SPK_N

## TP301 - MIC_3V3
MPN: PCB copper test point. Footprint: TestPoint:TestPoint_Pad_D1.5mm.
Probe access; no purchased component
Pins: 1=MIC_3V3

## TP302 - PI_5V
MPN: PCB copper test point. Footprint: TestPoint:TestPoint_Pad_D1.5mm.
Probe access; no purchased component
Pins: 1=PI_5V

## TP303 - GND
MPN: PCB copper test point. Footprint: TestPoint:TestPoint_Pad_D1.5mm.
Probe access; no purchased component
Pins: 1=GND

## U8 - SN74LVC1G07DBVR
MPN: SN74LVC1G07DBVR. Footprint: Package_TO_SOT_SMD:SOT-23-5.
5.5V-tolerant open drain and Ioff isolate Pi from connector +5V faults.
Pins: 1=NC, 2=JAW_PWM, 3=GND, 4=JAW_OD, 5=PI_3V3

## R401 - 100k 1%
MPN: RC0805FR-07100KL. Footprint: Resistor_SMD:R_0805_2012Metric.
Boot-low PWM.
Pins: 1=JAW_PWM, 2=GND

## R402 - 4.7k 1%
MPN: RC0805FR-074K7L. Footprint: Resistor_SMD:R_0805_2012Metric.
5V signal pull-up before protective series resistor.
Pins: 1=SERVO_5V, 2=JAW_OD

## R403 - 1k 1%
MPN: RC0805FR-071KL. Footprint: Resistor_SMD:R_0805_2012Metric.
A short to +5V sinks at most about 5.3mA; ground short limited by pull-up.
Pins: 1=JAW_OD, 2=JAW_SIG

## C401 - 100n
MPN: C0805C104K5RACTU. Footprint: Capacitor_SMD:C_0805_2012Metric.
Buffer bypass.
Pins: 1=PI_3V3, 2=GND

## J4 - Jaw: GND +5V SIG
MPN: TSW-103-07-G-S. Footprint: Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical.
Standard servo plug; clearly mark both sides; retention clip recommended.
Pins: 1=GND, 2=SERVO_5V, 3=JAW_SIG

## U9 - TL431AIDBZR
MPN: TL431AIDBZR. Footprint: Package_TO_SOT_SMD:SOT-23.
Reference controls regenerative shunt. Verify dynamic stability with actual servo.
Pins: 1=REGEN_K, 2=REGEN_REF, 3=GND

## R404 - 12.4k 0.1%
MPN: RT0805BRD0712K4L. Footprint: Resistor_SMD:R_0805_2012Metric.
2.495*(1+12.4/10)=5.589V nominal dump threshold.
Pins: 1=SERVO_5V, 2=REGEN_REF

## R405 - 10k 0.1%
MPN: RT0805BRD0710KL. Footprint: Resistor_SMD:R_0805_2012Metric.
Shunt reference bottom.
Pins: 1=REGEN_REF, 2=GND

## R406 - 2.2k 1%
MPN: RC0805FR-072K2L. Footprint: Resistor_SMD:R_0805_2012Metric.
Cathode bias and gate pull-up, ~1.4mA at clamp onset.
Pins: 1=SERVO_5V, 2=REGEN_K

## R407 - 100 1%
MPN: RC0805FR-07100RL. Footprint: Resistor_SMD:R_0805_2012Metric.
Isolate capacitive FET gate.
Pins: 1=REGEN_K, 2=REGEN_GATE

## Q3 - AO3401A
MPN: AO3401A. Footprint: Package_TO_SOT_SMD:SOT-23.
PMOS shunts excess servo rail energy into R408.
Pins: 1=REGEN_GATE, 2=SERVO_5V, 3=DUMP

## R408 - 10ohm 5W
MPN: SQP500JB-10R. Footprint: Resistor_THT:R_Axial_Power_L25.0mm_W9.0mm_P30.48mm.
At 5.6V absorbs up to 3.14W. Mount 5mm above PCB, away from plastic.
Pins: 1=DUMP, 2=GND

## SW1 - Momentary button
MPN: B3F-1000. Footprint: Button_Switch_THT:SW_PUSH_6mm_H4.3mm.
Normally-open, front plunger access. No identity semantics.
Pins: 1=BUTTON_SWITCH, 2=GND

## R409 - 1k 1%
MPN: RC0805FR-071KL. Footprint: Resistor_SMD:R_0805_2012Metric.
Limits switch discharge current.
Pins: 1=BUTTON_SWITCH, 2=BUTTON_RC

## R410 - 100k 1%
MPN: RC0805FR-07100KL. Footprint: Resistor_SMD:R_0805_2012Metric.
Release RC time constant 10ms.
Pins: 1=PI_3V3, 2=BUTTON_RC

## C402 - 100n
MPN: C0805C104K5RACTU. Footprint: Capacitor_SMD:C_0805_2012Metric.
Press time constant ~0.1ms; software requires 30ms stable both edges.
Pins: 1=BUTTON_RC, 2=GND

## U10 - SN74LVC1G17DBVR
MPN: SN74LVC1G17DBVR. Footprint: Package_TO_SOT_SMD:SOT-23-5.
Schmitt buffer converts slow RC edges to clean logic.
Pins: 1=NC, 2=BUTTON_RC, 3=GND, 4=BUTTON_N, 5=PI_3V3

## C403 - 100n
MPN: C0805C104K5RACTU. Footprint: Capacitor_SMD:C_0805_2012Metric.
Schmitt buffer bypass.
Pins: 1=PI_3V3, 2=GND

## R411 - 680 1%
MPN: RC0805FR-07680RL. Footprint: Resistor_SMD:R_0805_2012Metric.
About 2mA for green LED Vf~2V.
Pins: 1=LED_GPIO, 2=LED_A

## D3 - Green status LED
MPN: WP710A10SGC. Footprint: LED_THT:LED_D3.0mm.
Visible via printed light pipe.
Pins: 1=GND, 2=LED_A

## TP401 - JAW_SIG
MPN: PCB copper test point. Footprint: TestPoint:TestPoint_Pad_D1.5mm.
Probe access; no purchased component
Pins: 1=JAW_SIG

## TP402 - SERVO_EN
MPN: PCB copper test point. Footprint: TestPoint:TestPoint_Pad_D1.5mm.
Probe access; no purchased component
Pins: 1=SERVO_EN

## TP403 - BUTTON_N
MPN: PCB copper test point. Footprint: TestPoint:TestPoint_Pad_D1.5mm.
Probe access; no purchased component
Pins: 1=BUTTON_N

## TP404 - GND
MPN: PCB copper test point. Footprint: TestPoint:TestPoint_Pad_D1.5mm.
Probe access; no purchased component
Pins: 1=GND

## R114 - 10k 1%
MPN: RC0805FR-0710KL. Footprint: Resistor_SMD:R_0805_2012Metric.
10k/10k EN divider; 2.55 V nominal at 5.1 V input, with D101 fault clamp.
Pins: 1=PD_5V, 2=PI_EN_UVLO

## R115 - 10k 1%
MPN: RC0805FR-0710KL. Footprint: Resistor_SMD:R_0805_2012Metric.
10k/10k EN divider; 2.55 V nominal at 5.1 V input, with D101 fault clamp.
Pins: 1=PI_EN_UVLO, 2=GND

## D101 - 5.1V EN clamp
MPN: MMSZ5V1T1G. Footprint: Diode_SMD:D_SOD-123.
Cathode to EN, anode to ground. Limits EN fault voltage; R114 limits clamp current.
Pins: 1=PI_EN_UVLO, 2=GND

## U11 - 74AUP1G74DC
MPN: 74AUP1G74DC,125. Footprint: Package_SO:VSSOP-8_2.3x2mm_P0.5mm.
Schmitt-input arm latch; active-low supply-good clears Q asynchronously. New request rising edge required after recovery. Nexperia AUP part, 3.3V only.
Pins: 1=SERVO_REQUEST, 2=PI_3V3, 3=NC, 4=GND, 5=SERVO_ARMED, 6=SUPPLY_OK, 7=PI_3V3, 8=PI_3V3

## C112 - 100n
MPN: C0805C104K5RACTU. Footprint: Capacitor_SMD:C_0805_2012Metric.
Local bypass for U11 arm latch.
Pins: 1=PI_3V3, 2=GND
