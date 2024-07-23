#
# Edition: tt04
# Address: 325 (tt project selection address)
# Project: tt04-muldiv4
# Title:   MULDIV unit (4-bit signed/unsigned)
#
# CLOCK: 0  (no clock)
#
#
# How to use:
#   Connect a TT04 board into USB.
#   With Chrome brower navigate to https://commander.tinytapeout.com/
#   Connect to board with USB Serial
#   CONFIG:
#     Clock set to 0 Hz (disabled) [click SET]
#     Project 325 [click SELECT]
#   REPL:
#     Paste this script into
#
#   It maybe necessary to split the file into 3 parts as I found the serial
#   interface would block (seemingly deadlock on the MicroPython device)
#   if there was too much data.
#
#   I have marked a suitable split location with ##### SPLIT MARKER #####
#
#
# Copyright (c) 2024 Darryl L. Miles
# SPDX-License-Identifier: Apache-2.0
#
from machine import Pin

# Alternatively you can use a terminal/minicom/PuTTY on ttyAC)/COMx
#  issue these two command on power up.  Then Ctrl-E and upload/paste 
#  in this script, using Ctrl-D to complete.
# machine.reset()
stopClocking()

# HOTFIX some versions of firmware might need this
# FIXUP missing pin definitions (they were missing in my f/w)
# FORCE them as ttboard/demoboard.py:396 of __getattr__ raise AttributeError
#if tt.pin_out1 is None:
tt.pin_out1 = machine.Pin(6, mode=Pin.IN, pull=Pin.PULL_DOWN)

#if tt.pin_out2 is None:
tt.pin_out2 = machine.Pin(7, mode=Pin.IN, pull=Pin.PULL_DOWN)

#if tt.pin_out3 is None:
tt.pin_out3 = machine.Pin(8, mode=Pin.IN, pull=Pin.PULL_DOWN)


# Setup some easy access variables
EDIVOVER = tt.pin_uio4 # Pin(GPIO_UIO[4], Pin.IN)
EDIVZERO = tt.pin_uio5 # Pin(GPIO_UIO[5], Pin.IN)
OPSIGNED = tt.pin_uio6 # Pin(GPIO_UIO[6], Pin.OUT)
MULDIV   = tt.pin_uio7 # Pin(GPIO_UIO[7], Pin.OUT)
A0       = tt.pin_in0  # Pin(GPIO_UI_IN[0], Pin.OUT)
A1       = tt.pin_in1  # Pin(GPIO_UI_IN[1], Pin.OUT)
A2       = tt.pin_in2  # Pin(GPIO_UI_IN[2], Pin.OUT)
A3       = tt.pin_in3  # Pin(GPIO_UI_IN[3], Pin.OUT)
B0       = tt.pin_in4  # Pin(GPIO_UI_IN[4], Pin.OUT)
B1       = tt.pin_in5  # Pin(GPIO_UI_IN[5], Pin.OUT)
B2       = tt.pin_in6  # Pin(GPIO_UI_IN[6], Pin.OUT)
B3       = tt.pin_in7  # Pin(GPIO_UI_IN[7], Pin.OUT)
# No GPIO_UO_OUT global exists
RES0     = tt.pin_out0 # Pin(GPIO_UO_OUT[0], Pin.IN)
RES1     = tt.pin_out1 # Pin(GPIO_UO_OUT[1], Pin.IN)
RES2     = tt.pin_out2 # Pin(GPIO_UO_OUT[2], Pin.IN)
RES3     = tt.pin_out3 # Pin(GPIO_UO_OUT[3], Pin.IN)
RES4     = tt.pin_out4 # Pin(GPIO_UO_OUT[4], Pin.IN)
RES5     = tt.pin_out5 # Pin(GPIO_UO_OUT[5], Pin.IN)
RES6     = tt.pin_out6 # Pin(GPIO_UO_OUT[6], Pin.IN)
RES7     = tt.pin_out7 # Pin(GPIO_UO_OUT[7], Pin.IN)

# Setup buses
A = [A3, A2, A1, A0]
B = [B3, B2, B1, B0]
P = [RES7, RES6, RES5, RES4, RES3, RES2, RES1, RES0]
Q = [RES3, RES2, RES1, RES0]
R = [RES7, RES6, RES5, RES4]

WIDTH = 4
PWIDTH = 8
MASK = (1 << WIDTH) - 1

verbose = 1


def debug(level, *kwargs) -> None:
    if verbose >= level:
        print(*kwargs)


# create base2 number, MSB first
def binval(value: int, width: int = 1) -> str:
    assert width >= 0
    s = ''
    for bitid in range(width):
        bitval = 1 << bitid
        if (value & bitval) != 0:
            s = f"1{s}"
        else:
            s = f"0{s}"
    return s


def u2s(value: int, width: int) -> int: # unsigned to signed at width
    assert width >= 0
    unsigned_max_plus_one = 1 << width
    unsigned_max = unsigned_max_plus_one - 1
    signed_max_plus_one = (1 << (width - 1))
    signed_max = signed_max_plus_one - 1
    if value < 0 or value > unsigned_max:
        value &= unsigned_max
    if value > signed_max:
        value -= unsigned_max_plus_one
    return value


def s2u(value: int, width: int) -> int: # signed to unsigned at width
    assert width >= 0
    unsigned_max_plus_one = 1 << width
    unsigned_max = unsigned_max_plus_one - 1
    return value & unsigned_max


def veribinval(value: int, width: int = 1) -> str:
    assert width >= 1
    s = binval(value, width)
    return f"{width}\'b{s}"


def veridecval(value: int, width: int = 1) -> str:
    assert width >= 1
    value = s2u(value, width)
    return f"{width}\'d{value}"


# None = -8 to +15.
def fix_range(value: int, signed: int = None) -> int:
    sv = u2s(value, WIDTH)
    uv = s2u(value, WIDTH)
    if signed == True:
        return sv
    elif signed == False:
        return uv
    if value < 0:
        return sv
    return uv


def rdbus(pins: Sequence[Any]) -> int: # read a bus of Pin
    v = 0
    w = len(pins)
    for i, pin in enumerate(pins): # MSB first
        bitid = w - i - 1
        v <<= 1
        vv = '0'
        # MuxedSelection on tt.out3 makes this not have consistent interface
        if pin() != 0: # pin.value()
            v |= 1
            vv = '1'
        debug(2, f"rd({bitid}) = {vv} {(v & 1) != 0}") # verbose
    return v


def wrbus(pins: Sequence[Any], value: int) -> None: # write a bus of Pin
    nvalue = fix_range(value)
    if nvalue != value:
        print(f"WARNING: Input out of range {value} 0..15 or -7...8 using {nvalue}")
    w = len(pins)
    for i, pin in enumerate(pins): # pins is MSB first
        bitid = w - i - 1
        bitval = 1 << bitid
        bitbf = True if (nvalue & bitval) != 0 else False
        pin(bitbf) # invoke as function to set value
        debug(2, f"wr({bitid}) = {bitbf} {pin}") # verbose


def prbus(pins: Sequence[Any], width: int = None) -> None:
    width = len(pins) if width is None else width
    v = rdbus(pins)
    sv = u2s(v, width)
    print(f"{v} {sv:5d}   0x{v:x}   {binval(v, width)}b  {veribinval(v, width)}  {veridecval(v, width)}")


def div_status(signed: bool = False) -> None:
    edivover = EDIVOVER.value()
    edivzero = EDIVZERO.value()
    d_edivover = ' EDIVOVER' if edivover else ''
    d_edivzero = ' EDIVZERO' if edivzero else ''
    qvalue = rdbus(Q)
    if signed:
        qvalue = u2s(qvalue, WIDTH)
    d_qvalue = f"Q=[{qvalue:2d}  0x{qvalue:x}  {binval(qvalue, WIDTH)}  {veribinval(qvalue, WIDTH)}  {veridecval(qvalue, WIDTH)}]"
    print(d_qvalue)
    rvalue = rdbus(R)
    if signed:
        rvalue = u2s(rvalue, WIDTH)
    d_rvalue = f"R=[{rvalue:2d}  0x{rvalue:x}  {binval(rvalue, WIDTH)}  {veribinval(rvalue, WIDTH)}  {veridecval(rvalue, WIDTH)}]"
    print(d_rvalue)
    str = f"E={d_edivover}{d_edivzero}"
    print(str)


def mul_status(signed: bool = False) -> None:
    # Error signal outputs ignored for multiple
    pvalue = rdbus(P)
    sv = u2s(pvalue, PWIDTH)
    d_pvalue = f"P=[{pvalue:2d} {sv:5d}   0x{pvalue:x}   {binval(pvalue, PWIDTH)}  {veribinval(pvalue, PWIDTH)}  {veridecval(pvalue, PWIDTH)}]"
    print(d_pvalue)


def status() -> str:
    v_muldiv = MULDIV.value()
    v_opsigned = OPSIGNED.value()
    d_muldiv = 'Divide' if(v_muldiv) != 0 else 'Multiply'
    d_opsigned = 'Signed' if(v_opsigned) != 0 else 'Unsigned'
    print(f"MULDIV={v_muldiv} [{d_muldiv}]    OPSIGNED={v_opsigned}  [{d_opsigned}]")
    v_a = rdbus(A)
    v_b = rdbus(B)
    print(f"     A={v_a} [0x{v_a:x}]           B={v_b}  [0x{v_b:x}]")
    if MULDIV.value(): # True == DIV
        return div_status(OPSIGNED.value() != 0)
    else:
        return mul_status(OPSIGNED.value() != 0)


def wait() -> None:
    # NOP for now but represents non-instant expection for results to be available
    return


##### SPLIT MARKER #####

def validate(a: Numeric, b: Numeric, signed: bool = False) -> None:
    if signed:
        if a < -8 or a > 7:
            raise Exception(f"A out-of-range ({a} -8..7)")
        if b < -8 or b > 7:
            raise Exception(f"B out-of-range ({b} -8..7)")
    else:
        if a < 0 or a > 15:
            raise Exception(f"A out-of-range ({a} 0..15)")
        if b < 0 or b > 15:
            raise Exception(f"B out-of-range ({b} 0..15)")


def div_op(a: Number, b: Number, signed: bool = False) -> int:	# Generic DIV
    validate(a, b, signed)
    MULDIV.on()		# Divide mode
    OPSIGNED(signed)
    wrbus(A, a)
    wrbus(B, b)
    op = 'S' if signed else 'U'
    if b == 0:
        expect = 'EDIVZERO'
        d_expect = f"{expect}"
    else:
        qexpect = int(a / b)
        rexpect = int(a % b)
        d_expect = f"Q=[{qexpect} 0x{int(qexpect):x} {veribinval(qexpect, WIDTH)}]"
        d_expect += f" R=[{rexpect} 0x{int(rexpect):x} {veribinval(rexpect, WIDTH)}]"
    print(f"DIV{op} A={a} B={b}  expect={d_expect}")
    wait()
    div_status()
    return qr(rdbus(Q), rdbus(R))


def divs_op(a: Number, b: Number) -> None: # Signed DIV
    return div_op(a, b, True)


def divu_op(a: Number, b: Number) -> None: # Unsigned DIV
    return div_op(a, b, False)


def mul_op(a: Number, b: Number, signed: bool = False) -> int:	# Generic MUL
    validate(a, b, signed)
    MULDIV.off()	# Multiply mode
    OPSIGNED(signed)
    wrbus(A, a)
    wrbus(B, b)
    op = 'S' if signed else 'U'
    expect = a * b
    uexpect = expect & MASK
    print(f"MUL{op} A={a} B={b}  expect=[{expect} 0x{uexpect:x} {veribinval(expect, WIDTH)}]")
    wait()
    mul_status()
    p = rdbus(P)
    if signed:
        p = u2s(p, PWIDTH) # interpret data into Python int type
    return p


def muls_op(a: Number, b: Number) -> None: # Signed MUL
    return mul_op(a, b, True)


def mulu_op(a: Number, b: Number) -> None: # Unsigned MUL
    return mul_op(a, b, False)


def passfail(expect: int, actual: int, expect_edivzero: bool = False, expect_edivover: bool = False) -> bool:
    actual_edivzero = EDIVZERO.value()
    actual_edivover = EDIVOVER.value()
    edivzero_ok = expect_edivzero == actual_edivzero
    edivover_ok = expect_edivover == actual_edivover
    result_ok = expect == actual
    bf = False
    # When EDIVZERO (or EDIVOVER) disregard result output
    if ( expect_edivzero or expect_edivover ) and edivzero_ok and edivover_ok:
        print("PASS")
        bf = True
    elif result_ok and edivzero_ok and edivzero_ok:
        print("PASS")
        bf = True
    else:
        print("FAIL")
    return bf


def test_one(fail_count: int, expect: int, func: Callable[[None],int], expect_edivzero: bool = False, expect_edivover: bool = False) -> int:
    actual = func()
    bf = passfail(expect, actual, expect_edivzero, expect_edivover)
    if not bf:
        fail_count += 1
    return fail_count


# Merge QR (4bit each) into 8bit value for test_one()
def qr(q: int, r: int) -> int:
    res = s2u(q, WIDTH) & MASK
    res |= (s2u(r, WIDTH) & MASK) << WIDTH
    return res


def test_mulu(fail_count: int) -> int:
    # MULU
    fail_count = test_one(fail_count, 0,     lambda: mulu_op(0,  0))
    fail_count = test_one(fail_count, 0,     lambda: mulu_op(1,  0))
    fail_count = test_one(fail_count, 0,     lambda: mulu_op(15, 0))
    #
    fail_count = test_one(fail_count, 0,     lambda: mulu_op(0,  1))
    fail_count = test_one(fail_count, 1,     lambda: mulu_op(1,  1))
    fail_count = test_one(fail_count, 15,    lambda: mulu_op(15, 1))
    #
    fail_count = test_one(fail_count, 0,     lambda: mulu_op(0,  2))
    fail_count = test_one(fail_count, 2,     lambda: mulu_op(1,  2))
    fail_count = test_one(fail_count, 14,    lambda: mulu_op(7,  2))
    fail_count = test_one(fail_count, 16,    lambda: mulu_op(8,  2))
    fail_count = test_one(fail_count, 30,    lambda: mulu_op(15, 2))
    #
    fail_count = test_one(fail_count, 0,     lambda: mulu_op(0,  15))
    fail_count = test_one(fail_count, 15,    lambda: mulu_op(1,  15))
    fail_count = test_one(fail_count, 105,   lambda: mulu_op(7,  15))
    fail_count = test_one(fail_count, 120,   lambda: mulu_op(8,  15))
    fail_count = test_one(fail_count, 225,   lambda: mulu_op(15, 15))
    return fail_count


def test_muls(fail_count: int) -> int:
    # MULS
    fail_count = test_one(fail_count, 0,     lambda: muls_op(0,  0))
    fail_count = test_one(fail_count, 0,     lambda: muls_op(7,  0))
    fail_count = test_one(fail_count, 0,     lambda: muls_op(-8, 0))
    #
    fail_count = test_one(fail_count, 0,     lambda: muls_op(0,  1))
    fail_count = test_one(fail_count, 7,     lambda: muls_op(7,  1))
    fail_count = test_one(fail_count, -8,    lambda: muls_op(-8, 1))
    #
    fail_count = test_one(fail_count, 0,     lambda: muls_op(0,  2))
    fail_count = test_one(fail_count, 14,    lambda: muls_op(7,  2))
    fail_count = test_one(fail_count, -16,   lambda: muls_op(-8, 2))
    fail_count = test_one(fail_count, -14,   lambda: muls_op(-7, 2))
    fail_count = test_one(fail_count, -2,    lambda: muls_op(-1, 2))
    #
    fail_count = test_one(fail_count, 0,     lambda: muls_op(0,  7))
    fail_count = test_one(fail_count, 49,    lambda: muls_op(7,  7))
    fail_count = test_one(fail_count, -56,   lambda: muls_op(-8, 7))
    fail_count = test_one(fail_count, -49,   lambda: muls_op(-7, 7))
    fail_count = test_one(fail_count, -7,    lambda: muls_op(-1, 7))
    #
    fail_count = test_one(fail_count, 0,     lambda: muls_op(0,  -1))
    fail_count = test_one(fail_count, -1,    lambda: muls_op(1,  -1))
    fail_count = test_one(fail_count, -7,    lambda: muls_op(7,  -1))
    fail_count = test_one(fail_count, 8,     lambda: muls_op(-8, -1))
    fail_count = test_one(fail_count, 7,     lambda: muls_op(-7, -1))
    fail_count = test_one(fail_count, 1,     lambda: muls_op(-1, -1))
    #
    fail_count = test_one(fail_count, 0,     lambda: muls_op(0,  -8))
    fail_count = test_one(fail_count, -8,    lambda: muls_op(1,  -8))
    fail_count = test_one(fail_count, -56,   lambda: muls_op(7,  -8))
    fail_count = test_one(fail_count, 64,    lambda: muls_op(-8, -8))
    fail_count = test_one(fail_count, 56,    lambda: muls_op(-7, -8))
    fail_count = test_one(fail_count, 8,     lambda: muls_op(-1, -8))
    return fail_count


##### SPLIT MARKER #####

def test_divu(fail_count: int) -> int:
    # DIVU
    fail_count = test_one(fail_count, None,        lambda: divu_op(0,   0), expect_edivzero=True)
    fail_count = test_one(fail_count, None,        lambda: divu_op(1,   0), expect_edivzero=True)
    fail_count = test_one(fail_count, None,        lambda: divu_op(7,   0), expect_edivzero=True)
    fail_count = test_one(fail_count, None,        lambda: divu_op(8,   0), expect_edivzero=True)
    fail_count = test_one(fail_count, None,        lambda: divu_op(14,  0), expect_edivzero=True)
    fail_count = test_one(fail_count, None,        lambda: divu_op(15,  0), expect_edivzero=True)
    #
    fail_count = test_one(fail_count, qr(0,  0),   lambda: divu_op(0,   1))
    fail_count = test_one(fail_count, qr(1,  0),   lambda: divu_op(1,   1))
    fail_count = test_one(fail_count, qr(7,  0),   lambda: divu_op(7,   1))
    fail_count = test_one(fail_count, qr(8,  0),   lambda: divu_op(8,   1))
    fail_count = test_one(fail_count, qr(14, 0),   lambda: divu_op(14,  1))
    fail_count = test_one(fail_count, qr(15, 0),   lambda: divu_op(15,  1))
    #
    fail_count = test_one(fail_count, qr(0, 0),    lambda: divu_op(0,   2))
    fail_count = test_one(fail_count, qr(0, 1),    lambda: divu_op(1,   2))
    fail_count = test_one(fail_count, qr(0, 7),    lambda: divu_op(7,   8))
    fail_count = test_one(fail_count, qr(0, 8),    lambda: divu_op(8,   9))
    fail_count = test_one(fail_count, qr(0, 9),    lambda: divu_op(9,  10))
    fail_count = test_one(fail_count, qr(0, 14),   lambda: divu_op(14, 15))
    #
    fail_count = test_one(fail_count, qr(14,  0),  lambda: divu_op(14,  1))
    fail_count = test_one(fail_count, qr(7,   0),  lambda: divu_op(14,  2))
    fail_count = test_one(fail_count, qr(4,   2),  lambda: divu_op(14,  3))
    fail_count = test_one(fail_count, qr(15,  0),  lambda: divu_op(15,  1))
    fail_count = test_one(fail_count, qr(7,   1),  lambda: divu_op(15,  2))
    fail_count = test_one(fail_count, qr(5,   0),  lambda: divu_op(15,  3))
    #
    fail_count = test_one(fail_count, qr(0, 0),    lambda: divu_op(0,  15))
    fail_count = test_one(fail_count, qr(0, 1),    lambda: divu_op(1,  15))
    fail_count = test_one(fail_count, qr(0, 7),    lambda: divu_op(7,  15))
    fail_count = test_one(fail_count, qr(0, 8),    lambda: divu_op(8,  15))
    fail_count = test_one(fail_count, qr(0, 14),   lambda: divu_op(14, 15))
    fail_count = test_one(fail_count, qr(1, 0),    lambda: divu_op(15, 15))
    return fail_count


def test_divs(fail_count: int) -> int:
    # DIVS
    fail_count = test_one(fail_count, None,        lambda: divs_op(0,  0), expect_edivzero=True)
    fail_count = test_one(fail_count, None,        lambda: divs_op(1,  0), expect_edivzero=True)
    fail_count = test_one(fail_count, None,        lambda: divs_op(7,  0), expect_edivzero=True)
    fail_count = test_one(fail_count, None,        lambda: divs_op(-8, 0), expect_edivzero=True)
    fail_count = test_one(fail_count, None,        lambda: divs_op(-7, 0), expect_edivzero=True)
    fail_count = test_one(fail_count, None,        lambda: divs_op(-1, 0), expect_edivzero=True)
    #
    fail_count = test_one(fail_count, qr(   0,  0),  lambda: divs_op( 0,  1))
    fail_count = test_one(fail_count, qr(   1,  0),  lambda: divs_op( 1,  1))
    fail_count = test_one(fail_count, qr(   7,  0),  lambda: divs_op( 7,  1))
    fail_count = test_one(fail_count, qr(  -8,  0),  lambda: divs_op(-8,  1))
    fail_count = test_one(fail_count, qr(  -7,  0),  lambda: divs_op(-7,  1))
    fail_count = test_one(fail_count, qr(  -1,  0),  lambda: divs_op(-1,  1))
    #
    fail_count = test_one(fail_count, qr(   0,  0),  lambda: divs_op( 0,  2))
    fail_count = test_one(fail_count, qr(   0,  1),  lambda: divs_op( 1,  2))
    fail_count = test_one(fail_count, qr(   3,  1),  lambda: divs_op( 7,  2))
    fail_count = test_one(fail_count, qr(  -4,  0),  lambda: divs_op(-8,  2))
    fail_count = test_one(fail_count, qr(  -3, -1),  lambda: divs_op(-7,  2))
    fail_count = test_one(fail_count, qr(   0, -1),  lambda: divs_op(-1,  2))
    #
    fail_count = test_one(fail_count, qr(   0,  0),  lambda: divs_op( 0,  7))
    fail_count = test_one(fail_count, qr(   0,  1),  lambda: divs_op( 1,  7))
    fail_count = test_one(fail_count, qr(   1,  0),  lambda: divs_op( 7,  7))
    fail_count = test_one(fail_count, qr(  -1, -1),  lambda: divs_op(-8,  7))
    fail_count = test_one(fail_count, qr(  -1,  0),  lambda: divs_op(-7,  7))
    fail_count = test_one(fail_count, qr(   0, -1),  lambda: divs_op(-1,  7))
    #
    fail_count = test_one(fail_count, qr(   0,  0),  lambda: divs_op( 0, -8))
    fail_count = test_one(fail_count, qr(   0,  1),  lambda: divs_op( 1, -8))
    fail_count = test_one(fail_count, qr(   0,  7),  lambda: divs_op( 7, -8))
    fail_count = test_one(fail_count, qr(   1,  0),  lambda: divs_op(-8, -8))
    fail_count = test_one(fail_count, qr(   0, -7),  lambda: divs_op(-7, -8))
    fail_count = test_one(fail_count, qr(   0, -1),  lambda: divs_op(-1, -8))
    #
    fail_count = test_one(fail_count, qr(   0,  0),  lambda: divs_op( 0, -7))
    fail_count = test_one(fail_count, qr(   0,  1),  lambda: divs_op( 1, -7))
    fail_count = test_one(fail_count, qr(  -1,  0),  lambda: divs_op( 7, -7))
    fail_count = test_one(fail_count, qr(   1, -1),  lambda: divs_op(-8, -7))
    fail_count = test_one(fail_count, qr(   1,  0),  lambda: divs_op(-7, -7))
    fail_count = test_one(fail_count, qr(   0, -1),  lambda: divs_op(-1, -7))
    #
    fail_count = test_one(fail_count, qr(   0,  0),  lambda: divs_op( 0, -1))
    fail_count = test_one(fail_count, qr(  -1,  0),  lambda: divs_op( 1, -1))
    fail_count = test_one(fail_count, qr(  -7,  0),  lambda: divs_op( 7, -1))
    fail_count = test_one(fail_count, qr(  -8,  0),  lambda: divs_op(-8, -1))
    fail_count = test_one(fail_count, qr(   7,  0),  lambda: divs_op(-7, -1))
    fail_count = test_one(fail_count, qr(   1,  0),  lambda: divs_op(-1, -1))
    return fail_count


def test() -> bool:
    fail_count = 0
    fail_count = test_mulu(fail_count)
    fail_count = test_muls(fail_count)
    fail_count = test_divu(fail_count)
    fail_count = test_divs(fail_count)
    #
    if fail_count == 0:
        print("SUCCESS: ALL TESTS PASS")
        return True
    else:
        print(f"FAILURE: {fail_count} test(s) FAIL")
    return False


def environment_check() -> bool:
    ### FIXME can we perform an environment check, to prevent running against the wrong TT edition
    ## Unclear if I and query the firmwares power-on ROM check or config.ini data.
    if True:
        print("WARN: This project is for TT04 but this environment has NOT")
        print("WARN: been validated automatically Please manually check and")
        print("WARN: confirm TT04 is connected")
        print(" * Set Clock to 0")
        print(" * Select Project 325")
        print(" * Open REPL tab and load this script")
    return True


def project325_pin_setup():
    # This is delayed until after project selection because that assumes
    #  PMODs have been disconnected.
    tt.pin_uio4.init(mode=Pin.IN,  pull=Pin.PULL_DOWN) # EDIVOVER
    tt.pin_uio5.init(mode=Pin.IN,  pull=Pin.PULL_DOWN) # EDIVZERO
    tt.pin_uio6.init(mode=Pin.OUT, pull=Pin.PULL_DOWN) # OPSIGNED
    tt.pin_uio7.init(mode=Pin.OUT, pull=Pin.PULL_DOWN) # MULDIV
    # We don't really need to reconfigure or change these the
    #  defaults should be correct.
    #tt.pin_in0.init(mode=Pin.OUT,  pull=Pin.PULL_DOWN) # A0
    #tt.pin_in1.init(mode=Pin.OUT,  pull=Pin.PULL_DOWN) # A1
    #tt.pin_in2.init(mode=Pin.OUT,  pull=Pin.PULL_DOWN) # A2
    #tt.pin_in3.init(mode=Pin.OUT,  pull=Pin.PULL_DOWN) # A3
    #tt.pin_in4.init(mode=Pin.OUT,  pull=Pin.PULL_DOWN) # A4
    #tt.pin_in5.init(mode=Pin.OUT,  pull=Pin.PULL_DOWN) # A5
    #tt.pin_in6.init(mode=Pin.OUT,  pull=Pin.PULL_DOWN) # A6
    #tt.pin_in7.init(mode=Pin.OUT,  pull=Pin.PULL_DOWN) # A7
    #tt.pin_out0.init(mode=Pin.IN,  pull=Pin.PULL_DOWN) # RES0
    #tt.pin_out1.init(mode=Pin.IN,  pull=Pin.PULL_DOWN) # RES1
    #tt.pin_out2.init(mode=Pin.IN,  pull=Pin.PULL_DOWN) # RES2
    #tt.pin_out3.init(mode=Pin.IN,  pull=Pin.PULL_DOWN) # RES3
    #tt.pin_out4.init(mode=Pin.IN,  pull=Pin.PULL_DOWN) # RES4
    #tt.pin_out5.init(mode=Pin.IN,  pull=Pin.PULL_DOWN) # RES5
    #tt.pin_out6.init(mode=Pin.IN,  pull=Pin.PULL_DOWN) # RES6
    #tt.pin_out7.init(mode=Pin.IN,  pull=Pin.PULL_DOWN) # RES7


def project325_enable(force: bool = False):
    # check environment is TT04
    if not environment_check() and not force:
        printf(f"WARNING: Overide this halt with: project325_enable(force=True)")
        return
    # reset stuff (but not the REPL connection itself)
    stopClocking() #set_clock_hz(0)  # stop clock
    tt.nproject_rst(0)
    tt.project_clk(0)
    tt.shuttle.reset_and_clock_mux(325) # select_design(325)
    # enable project bidi pin directions
    project325_pin_setup()
    time.sleep_ms(1)
    tt.clock_project_once()
    tt.clock_project_once()
    tt.nproject_rst(1)
    # reset released
    #
    # set default state (MULU 1*1=1)
    print("project325_enable")
    MULDIV.off()
    OPSIGNED.off()
    wrbus(A, 1)
    wrbus(B, 1)
    status()


def project325_help():
    print("Help Info: ")
    print("  mul_op(a: Number, b: Number, signed: bool) - Execute MUL op")
    print("  div_op(a: Number, b: Number, signed: bool) - Execute DIV op")
    print("  status()             - Report Output Status")
    print("  test()               - Run some tests")
    print("  project325_enable()  - Active project")


project325_help()

environment_check()

### THE END
