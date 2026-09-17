#!/usr/bin/env python3
"""Set the RGB memory to one static colour. No dependencies; run as root.

    sudo ram-color              # red
    sudo ram-color 00FF00       # any hex colour
    sudo ram-color --probe      # only report what is there; writes nothing

The G.Skill Trident Z RGB sticks carry an ENE lighting controller on the
motherboard's SMBus, next to the memory's own SPD chips. The protocol is the
one OpenRGB documents (ENESMBusController): a 16-bit register address written
big-endian as a word to command 0x00, then a byte to 0x01 or a block to 0x03,
or a byte read back from 0x81. This does the handful of writes a static colour
needs, which is all OpenRGB was being installed for (2026-09-17).

Safety: it only ever addresses 0x70-0x7F, and only a device that passes ENE's
identity test (registers 0xA0-0xAF read back 0-15). The SPD chips at 0x50-0x53
and their page switches at 0x36/0x37 are never touched. The colour is applied,
not saved to the sticks' flash, so a boot unit sets it again each start.
"""

import ctypes
import fcntl
import glob
import os
import sys
import time

I2C_SLAVE = 0x0703
I2C_SMBUS = 0x0720
READ, WRITE = 1, 0
QUICK, BYTE_DATA, WORD_DATA, BLOCK_DATA = 0, 2, 3, 5

REG_DEVICE_NAME = 0x1000
REG_CONFIG_TABLE = 0x1C00
REG_DIRECT = 0x8020
REG_MODE = 0x8021
REG_APPLY = 0x80A0
COLORS_EFFECT_V1 = 0x8010
COLORS_EFFECT_V2 = 0x8160
APPLY = 0x01
MODE_STATIC = 0x01
# Remapped sticks live here. Unmapped ones all answer together at 0x77, which is
# fine for this: both get the same colour.
ADDRESSES = range(0x70, 0x80)


class Data(ctypes.Union):
    _fields_ = [("byte", ctypes.c_uint8), ("word", ctypes.c_uint16), ("block", ctypes.c_uint8 * 34)]


class Args(ctypes.Structure):
    _fields_ = [("read_write", ctypes.c_uint8), ("command", ctypes.c_uint8),
                ("size", ctypes.c_uint32), ("data", ctypes.POINTER(Data))]


class Device:
    def __init__(self, bus: int, address: int):
        if not 0x70 <= address <= 0x7F:
            raise ValueError(f"refusing to address 0x{address:02x}: outside the lighting range")
        self.fd, self.address = bus, address

    def _smbus(self, read_write, command, size, data=None):
        data = data or Data()
        fcntl.ioctl(self.fd, I2C_SLAVE, self.address)
        fcntl.ioctl(self.fd, I2C_SMBUS, Args(read_write, command, size, ctypes.pointer(data)))
        return data

    def quick(self):
        self._smbus(WRITE, 0, QUICK)

    def read_byte(self, command):
        return self._smbus(READ, command, BYTE_DATA).byte

    def _select(self, register):
        data = Data()
        data.word = ((register << 8) & 0xFF00) | ((register >> 8) & 0x00FF)
        self._smbus(WRITE, 0x00, WORD_DATA, data)

    def read(self, register):
        self._select(register)
        return self.read_byte(0x81)

    def write(self, register, value):
        self._select(register)
        data = Data()
        data.byte = value
        self._smbus(WRITE, 0x01, BYTE_DATA, data)

    def write_block(self, register, values):
        self._select(register)
        data = Data()
        data.block[0] = len(values)
        for index, value in enumerate(values, 1):
            data.block[index] = value
        self._smbus(WRITE, 0x03, BLOCK_DATA, data)

    def is_ene(self):
        try:
            self.quick()
            return all(self.read_byte(0xA0 + i) == i for i in range(16))
        except OSError:
            return False


def smbus() -> str:
    for name in glob.glob("/sys/bus/i2c/devices/i2c-*/name"):
        if open(name).read().startswith("SMBus I801"):
            return "/dev/" + name.split("/")[-2]
    sys.exit("no Intel SMBus adapter found (is i2c-dev loaded?)")


def main() -> int:
    probe = "--probe" in sys.argv
    wanted = next((a for a in sys.argv[1:] if not a.startswith("-")), "FF0000")
    red, green, blue = (int(wanted[i:i + 2], 16) for i in (0, 2, 4))
    if os.geteuid() != 0:
        sys.exit("run as root: the SMBus is root-only")

    path = smbus()
    bus = os.open(path, os.O_RDWR)
    sticks = [Device(bus, a) for a in ADDRESSES if Device(bus, a).is_ene()]
    if not sticks:
        print(f"no ENE lighting controllers on {path}")
        return 1
    status = 0
    for stick in sticks:
        name = bytes(stick.read(REG_DEVICE_NAME + i) for i in range(16)).split(b"\0")[0].decode("ascii", "replace")
        leds = stick.read(REG_CONFIG_TABLE + 0x02)
        if not 1 <= leds <= 16:
            print(f"0x{stick.address:02x} {name}: implausible LED count {leds}, skipped")
            status = 1
            continue
        # Older firmware keeps the colours at 0x8010, newer (AUMA/AUDA, DIMM_LED-0103) at 0x8160.
        effect = COLORS_EFFECT_V2 if name.startswith(("AUMA", "AUDA", "DIMM_LED-0103")) else COLORS_EFFECT_V1
        if probe:
            print(f"0x{stick.address:02x} {name}: {leds} LEDs, mode {stick.read(REG_MODE)}, "
                  f"direct {stick.read(REG_DIRECT)}, colours at 0x{effect:04x}")
            continue
        colours = [red, blue, green] * leds          # ENE stores each LED as R, B, G
        stick.write(REG_DIRECT, 0)
        stick.write_block(effect, colours)
        stick.write(REG_MODE, MODE_STATIC)
        stick.write(REG_APPLY, APPLY)
        time.sleep(0.05)
        back = [stick.read(effect + i) for i in range(len(colours))]
        ok = back == colours
        print(f"0x{stick.address:02x} {name}: {leds} LEDs set to #{wanted.upper()}"
              f"{'' if ok else f' (read back {bytes(back).hex()}, expected {bytes(colours).hex()})'}")
        status |= 0 if ok else 1
    return status


if __name__ == "__main__":
    sys.exit(main())
