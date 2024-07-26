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
#   With Chrome browser navigate to https://commander.tinytapeout.com/
#   Connect to board with USB Serial
#   CONFIG:
#     Clock set to 0 Hz (disabled) [click SET]
#     Project 325 [click SELECT]
#   REPL:
#     Paste this script into
#
#   It maybe necessary to split the file into 3 parts as I found the serial
#   interface would block (seemingly deadlock on the MicroPython device)
#   if there was too much data, maybe 8KiB is the limit?
#
#   I have marked a suitable split location with ##### SPLIT MARKER #####
#
#
# Copyright (c) 2024 Darryl L. Miles
# SPDX-License-Identifier: Apache-2.0
#
#
# vvv Don't worry about this comment it out if it causes you a problem
import sys
if sys.implementation.name != "micropython":
    from numbers import Number # does not exist in MicroPython
    # Currently private surrogate of APIs to help with PC host based development
    from tthostdevel import *
# ^^^ Don't worry about this comment it out if it causes you a problem

from machine import Pin
##### SPLIT MARKER #####

# Alternatively you can use a terminal/minicom/PuTTY on ttyACM0/COMx
#  and type in these two command on power up.  (Without comment hash '#' prefix)
#machine.reset()  # command one
stopClocking()  # command two
# Then Ctrl-E and upload/paste in this script (minicom Ctrl-A then Y), finally
#  using Ctrl-D to complete and bring back MicroPython REPL prompt.


# =====vvv FIRMWARE HOTFIX vvv=====
# HOTFIX some versions of firmware might need this
# FIXUP missing pin definitions (they were missing in my f/w)
# FORCE them as ttboard/demoboard.py:396 of __getattr__ raise AttributeError
#if tt.pin_out1 is None:
tt.pin_out1 = machine.Pin(6, mode=Pin.IN, pull=Pin.PULL_DOWN)

#if tt.pin_out2 is None:
tt.pin_out2 = machine.Pin(7, mode=Pin.IN, pull=Pin.PULL_DOWN)

#if tt.pin_out3 is None:
tt.pin_out3 = machine.Pin(8, mode=Pin.IN, pull=Pin.PULL_DOWN)
# =====^^^ FIRMWARE HOTFIX ^^^=====


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
MASK = (1 << WIDTH) - 1
PWIDTH = 8
PMASK = (1 << PWIDTH) - 1

verbose = 1


def debug(level, *kwargs) -> None:
    if verbose >= level:
        print(*kwargs)


# create base2 number, MSB first
# binval(123, 8) => "01111011"
def binval(value: int, width: int = 1) -> str:
    assert width >= 0, f"invalid width: {width}"
    s = ''
    for bitid in range(width):
        bitval = 1 << bitid
        if (value & bitval) != 0:
            s = f"1{s}"
        else:
            s = f"0{s}"
    return s


# u2s(123, 8) => -5
# u2s(6, 4) => 6
def u2s(value: int, width: int) -> int: # unsigned to signed at width
    assert type(value) is int, f"wrong type: {type(value)}"
    assert width >= 0, f"invalid width: {width}"
    unsigned_max_plus_one = 1 << width
    unsigned_max = unsigned_max_plus_one - 1
    signed_max_plus_one = (1 << (width - 1))
    signed_max = signed_max_plus_one - 1
    if value < 0 or value > unsigned_max:
        value &= unsigned_max
    if value > signed_max:
        value -= unsigned_max_plus_one
    return value


# s2u(-5, 8) => 123
# s2u(6, 4) => 6
def s2u(value: int, width: int) -> int: # signed to unsigned at width
    assert type(value) is int, f"wrong type: {type(value)}"
    assert width >= 0, f"invalid width: {width}"
    unsigned_max_plus_one = 1 << width
    unsigned_max = unsigned_max_plus_one - 1
    return value & unsigned_max


# veribinval(123, 8) => "8'b011111011"
def veribinval(value: int, width: int = 1) -> str:
    assert width >= 1
    s = binval(value, width)
    return f"{width}\'b{s}"


# veridecval(128, 8) => "8'd123"
# veridecval(3, 8, 3) => "8'd003"
def veridecval(value: int, width: int = 1, pad: int = 0) -> str:
    assert width >= 1
    value = s2u(value, width)
    s_value = f"{value}"
    if len(s_value) < pad:
        padlen = pad - len(s_value)
        s_value = ("0" * padlen) + s_value
    return f"{width}\'d{s_value}"


# None = -8 to +15 (accepts any input it can reliabliy move into range)
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


##### SPLIT MARKER #####
# read bus of pins into integer (bus is MSB first)
def rdbus(pins: Sequence[any]) -> int: # read a bus of Pin
    v = 0
    w = len(pins)
    for i, pin in enumerate(pins): # MSB first
        bitid = w - i - 1 # because we are MSB first
        v <<= 1
        vv = '0'
        # MuxedSelection on tt.out3 makes this not have consistent interface
        if pin() != 0: # pin.value()
            v |= 1
            vv = '1'
        debug(2, f"rd({bitid}) = {vv} {(v & 1) != 0}") # verbose
    return v


# write bus of pins from integer
def wrbus(pins: Sequence[any], value: int) -> None: # write a bus of Pin
    nvalue = fix_range(value)
    if nvalue != value:
        print(f"WARNING: Input out of range {value} 0..15 or -7...8 using {nvalue}")
    w = len(pins)
    for i, pin in enumerate(pins): # pins is MSB first
        bitid = w - i - 1 # because we are MSB first
        bitval = 1 << bitid
        bitbf = True if (nvalue & bitval) != 0 else False
        pin(bitbf) # invoke as function to set value
        debug(2, f"wr({bitid}) = {bitbf} {pin}") # verbose


# print bus of pins to console
def prbus(pins: Sequence[any], width: int = None) -> None:
    width = len(pins) if width is None else width
    v = rdbus(pins)
    uv = v & ((1 << width) - 1) # custom mask
    print(f"{v}  {u2s(v, width):5d}  0x{uv:x}   {veribinval(v, width)}  {veridecval(v, width)}")


##### SPLIT MARKER #####
# interpret output as divide operation result and show
def div_status(signed: bool = False) -> str:
    edivover = EDIVOVER.value()
    edivzero = EDIVZERO.value()
    a_error = []
    d_edivover = 'EDIVOVER' if edivover else ''
    d_edivzero = 'EDIVZERO' if edivzero else ''
    if edivover:
        a_error.append(d_edivover)
    if edivzero:
        a_error.append(d_edivzero)
    qvalue = rdbus(Q)
    if signed:
        qvalue = u2s(qvalue, WIDTH)
    d_qvalue = f"Q=[{qvalue:3} {u2s(qvalue, WIDTH):3} 0x{s2u(qvalue, WIDTH):02x}  {veribinval(qvalue, WIDTH)}  {veridecval(qvalue, WIDTH, 2)}] actual"
    print(d_qvalue)
    rvalue = rdbus(R)
    if signed:
        rvalue = u2s(rvalue, WIDTH)
    d_rvalue = f"R=[{rvalue:3} {u2s(rvalue, WIDTH):3} 0x{s2u(rvalue, WIDTH):02x}  {veribinval(rvalue, WIDTH)}  {veridecval(rvalue, WIDTH, 2)}] actual"
    print(d_rvalue)
    if len(a_error) > 0:
        rv = ' '.join(a_error)
        str = f"E={rv}"
        print(str)
    elif rvalue != 0:
        rv = f"{qvalue}r{rvalue}"
    else:
        rv = f"{qvalue}"
    return rv


##### SPLIT MARKER #####
# interpret output as multiply operation result and show
def mul_status(signed: bool = False) -> str:
    # Error signal outputs ignored for multiple
    pvalue = rdbus(P)
    sv = u2s(pvalue, PWIDTH)
    d_pvalue = f"P=[{pvalue:4} {u2s(pvalue, PWIDTH):4} 0x{s2u(pvalue, PWIDTH):02x} {veribinval(pvalue, PWIDTH)} {veridecval(pvalue, PWIDTH, 3)}] actual"
    print(d_pvalue)
    if signed:
        return f"{sv}"
    return f"{pvalue}"


# interpret output of last operation result and show
def status() -> str:
    v_muldiv = MULDIV.value()
    v_opsigned = OPSIGNED.value()
    d_muldiv = 'Divide' if(v_muldiv) != 0 else 'Multiply'
    d_opsigned = 'Signed' if(v_opsigned) != 0 else 'Unsigned'
    print(f"MULDIV={v_muldiv} [{d_muldiv}]    OPSIGNED={v_opsigned} [{d_opsigned}]")
    a = rdbus(A)
    b = rdbus(B)
    print(f"     A={a:4}  {u2s(a, WIDTH):4}  [0x{s2u(a, WIDTH):02x}]       B={b:4}  {u2s(b, WIDTH):4}  [0x{s2u(b, WIDTH):02x}]")
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


def div_compute_expect(a: Number, b: Number, signed: bool = False) -> tuple:
    if b == 0:
        qexpect = 'EDIVZERO'
        rexpect = None
    else:
        qexpect = int(a / b)
        rexpect = int(a % b)
    return (qexpect, rexpect)


def div_op(a: Number, b: Number, signed: bool = False, status: bool = False) -> any: # Generic DIV
    validate(a, b, signed)
    MULDIV.on()		# Divide mode
    OPSIGNED(signed)
    wrbus(A, a)
    wrbus(B, b)
    qexpect, rexpect = div_compute_expect(a, b, signed)
    op = 'S' if signed else 'U'
    if type(qexpect) is int:
        expr_expect = f"{qexpect} r {rexpect}"
    else:
        expr_expect = qexpect # str
    print(f"DIV{op} SIGNED={signed:<5} A={a:<3} B={b:<3} expr={a} / {b} = {expr_expect}")
    if type(qexpect) is int: # might be string EDIV0
        print(f"Q=[{qexpect:3} {u2s(qexpect, WIDTH):3} 0x{s2u(qexpect, WIDTH):02x}  {veribinval(qexpect, WIDTH)}  {veridecval(qexpect, WIDTH, 2)}] expect")
    if type(rexpect) is int: # might be None
        print(f"R=[{rexpect:3} {u2s(rexpect, WIDTH):3} 0x{s2u(rexpect, WIDTH):02x}  {veribinval(rexpect, WIDTH)}  {veridecval(rexpect, WIDTH, 2)}] expect")
    print(f"A=[{a:3} {u2s(a, WIDTH):3} 0x{s2u(a, WIDTH):02x}  {veribinval(a, WIDTH)}  {veridecval(a, WIDTH, 2)}]")
    print(f"B=[{b:3} {u2s(b, WIDTH):3} 0x{s2u(b, WIDTH):02x}  {veribinval(b, WIDTH)}  {veridecval(b, WIDTH, 2)}]")
    wait()
    s = div_status()
    if status:
        return s
    return qr(rdbus(Q), rdbus(R)) # 8bit


def divs_op(a: Number, b: Number) -> int: # Signed DIV
    return div_op(a, b, signed=True)


def divu_op(a: Number, b: Number) -> int: # Unsigned DIV
    return div_op(a, b, signed=False)


def divs_op_status(a: Number, b: Number) -> str: # Signed DIV
    return div_op(a, b, signed=True, status=True)


def divu_op_status(a: Number, b: Number) -> str: # Unsigned DIV
    return div_op(a, b, signed=False, status=True)


def mul_op(a: Number, b: Number, signed: bool = False, status: bool = False) -> any:	# Generic MUL
    validate(a, b, signed)
    MULDIV.off()	# Multiply mode
    OPSIGNED(signed)
    wrbus(A, a)
    wrbus(B, b)
    op = 'S' if signed else 'U'
    expect = a * b
    print(f"MUL{op} SIGNED={signed:<5} A={a:<3} B={b:<3} expr={a} * {b} = {expect}")
    print(f"P=[{expect:4} {u2s(expect, PWIDTH):4} 0x{s2u(expect, PWIDTH):02x} {veribinval(expect, PWIDTH)} {veridecval(expect, PWIDTH, 3)}] expect")
    print(f"A=[{a:4} {u2s(a, WIDTH):4} 0x{s2u(a, WIDTH):02x}     {veribinval(a, WIDTH)} {veridecval(a, WIDTH, 3)}]")
    print(f"B=[{b:4} {u2s(b, WIDTH):4} 0x{s2u(b, WIDTH):02x}     {veribinval(b, WIDTH)} {veridecval(b, WIDTH, 3)}]")
    wait()
    s = mul_status()
    p = rdbus(P)
    if signed:
        p = u2s(p, PWIDTH) # interpret data into Python int type
    if status:
        return s
    return p


def muls_op(a: Number, b: Number) -> int: # Signed MUL
    return mul_op(a, b, signed=True)


def mulu_op(a: Number, b: Number) -> int: # Unsigned MUL
    return mul_op(a, b, signed=False)


def muls_op_status(a: Number, b: Number) -> str: # Signed MUL
    return mul_op(a, b, signed=True, status=True)


def mulu_op_status(a: Number, b: Number) -> str: # Unsigned MUL
    return mul_op(a, b, signed=False, status=True)


# Make a decision given actual result and expectation if this is correct
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


# Perform a single test and accumulate fail_count
def test_one(fail_count: int, expect: int, func: Callable[[None],int], expect_edivzero: bool = False, expect_edivover: bool = False) -> int:
    actual = func() # run the operation
    bf = passfail(expect, actual, expect_edivzero, expect_edivover) # decide pass or fail
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
    fail_count = test_one(fail_count, 0,     lambda: mulu_op(7,  0))
    fail_count = test_one(fail_count, 0,     lambda: mulu_op(8,  0))
    fail_count = test_one(fail_count, 0,     lambda: mulu_op(15, 0))
    #
    fail_count = test_one(fail_count, 0,     lambda: mulu_op(0,  1))
    fail_count = test_one(fail_count, 1,     lambda: mulu_op(1,  1))
    fail_count = test_one(fail_count, 7,     lambda: mulu_op(7,  1))
    fail_count = test_one(fail_count, 8,     lambda: mulu_op(8,  1))
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
    fail_count = test_one(fail_count, 0,     lambda: muls_op(1,  0))
    fail_count = test_one(fail_count, 0,     lambda: muls_op(7,  0))
    fail_count = test_one(fail_count, 0,     lambda: muls_op(-8, 0))
    fail_count = test_one(fail_count, 0,     lambda: muls_op(-7,  0))
    fail_count = test_one(fail_count, 0,     lambda: muls_op(-1,  0))
    #
    fail_count = test_one(fail_count, 0,     lambda: muls_op(0,  1))
    fail_count = test_one(fail_count, 7,     lambda: muls_op(7,  1))
    fail_count = test_one(fail_count, -8,    lambda: muls_op(-8, 1))
    fail_count = test_one(fail_count, -7,    lambda: muls_op(-7, 1))
    fail_count = test_one(fail_count, -1,    lambda: muls_op(-1, 1))
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
    fail_count = test_one(fail_count, qr(   8,  0),  lambda: divs_op(-8, -1))
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


##### SPLIT MARKER #####
def environment_check() -> bool:
    ## perform an environment check, to prevent running against the wrong TT edition
    ## unclear if I and query the firmware power-on ROM check or config.ini data.
    is_correct_tt_edition = tt.chip_ROM.shuttle == 'tt04'
    if is_correct_tt_edition:
        print(f"READY: This project is for TT04 which matches tt.chip_ROM.shuttle={tt.chip_ROM.shuttle}")
        return True
    print("ERROR: The TT PCB that is attached has been unable to validated is the correct edition.")
    print("ERROR: This project needs: tt04")
    return False


def project325_pin_setup():
    # This is delayed until after project selection because that assumes
    #  PMODs (from using it for a previous project) have been disconnected
    #  as this project does not use any PMODs.
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
    #tt.pin_in4.init(mode=Pin.OUT,  pull=Pin.PULL_DOWN) # B0
    #tt.pin_in5.init(mode=Pin.OUT,  pull=Pin.PULL_DOWN) # B1
    #tt.pin_in6.init(mode=Pin.OUT,  pull=Pin.PULL_DOWN) # B2
    #tt.pin_in7.init(mode=Pin.OUT,  pull=Pin.PULL_DOWN) # B3
    #tt.pin_out0.init(mode=Pin.IN,  pull=Pin.PULL_DOWN) # RES0
    #tt.pin_out1.init(mode=Pin.IN,  pull=Pin.PULL_DOWN) # RES1
    #tt.pin_out2.init(mode=Pin.IN,  pull=Pin.PULL_DOWN) # RES2
    #tt.pin_out3.init(mode=Pin.IN,  pull=Pin.PULL_DOWN) # RES3
    #tt.pin_out4.init(mode=Pin.IN,  pull=Pin.PULL_DOWN) # RES4
    #tt.pin_out5.init(mode=Pin.IN,  pull=Pin.PULL_DOWN) # RES5
    #tt.pin_out6.init(mode=Pin.IN,  pull=Pin.PULL_DOWN) # RES6
    #tt.pin_out7.init(mode=Pin.IN,  pull=Pin.PULL_DOWN) # RES7


def project325_activate(force: bool = False):
    # check environment is TT04
    if not environment_check() and not force:
        printf(f"WARNING: Overide this halt with: project325_activate(force=True)")
        return
    # =====vvv UNIVERSAL PROJECT RESET SEQUENCE vvv=====
    # This sequence is expected to work for all projects.
    # This project (tt04/325) does not make use of N_RST or CLK inputs.
    # So this section is more for copy-and-paste general purpose use.
    tt.clock_project_stop() # stopClocking() #set_clock_hz(0)  # stop clock
    # tristate or set to input the BIDI ports (reset_and_clock_mux() actually
    #  does this already) but it is good to see it expressed here as a visibility
    #  explicit action in this sequence.
    tt.pins.safe_bidir()
    # once they are tristated return pin control back to RP2040
    tt.mode = RPMode.ASIC_RP_CONTROL
    #
    # Setup all control lines to zero (assumes all zero inputs is a good default starting
    #  state to leave reset condition)
    tt.project_nrst(False)
    tt.project_clk(False)
    tt.inputs_byte = 0 # ui_in = 8'b0
    tt.bidir_byte = 0  # uio_in = 8'b0
    #
    tt.shuttle.reset_and_clock_mux(325) # select_design(325)
    # perform project specific bidi pin direction setup (this is the custom bidi
    #  setup when leaving reset) from this point BIDI direction management is allowed
    #  to take place for this project.
    project325_pin_setup()
    # this sleep represents a delay over 1000 times larger than needed to allow power
    #  gating to occur over the entire project and decap to achieve supply rail stability
    #  just after project selection.
    time.sleep_ms(1)
    # we clock an extra time (first cycle is a throw away cycle we don't expect/need to work)
    #  just in case the first clock is not a perfect clock cycle (not a good duty cycle, not
    #  100% to +ve rail, all receivers are not fully powered, allows the clock to act as a
    #  gate/release for internal charged states).
    tt.clock_project_once()
    # this is considered the perfect synchronous reset clock cycle, this can be left in for
    #  any project and is harmless to async reset or unclocked projects that don't need it.
    tt.clock_project_once()
    # Finally we can release reset
    tt.project_nrst(True)
    # reset released
    # =====^^^ UNIVERSAL PROJECT RESET SEQUENCE ^^^=====
    #
    # If this project is a clocked project we can start the clock here with the first
    #  cycle the first out of reset.
    # This (tt04/325) is not a clocked project, so we don't need to enable it.
    #tt.clock_project_PWM(10_000_000)  #tt.set_clock_hz()
    #
    # Now the project takes over from this point on infrastructure is out the way.
    #
    # set default state (MULU 1*1=1)
    print("STATUS: Project 325 successfully activated")
    MULDIV.off()
    OPSIGNED.off()
    wrbus(A, 1)
    wrbus(B, 1)
    status()


def project325_help():
    print("Help Info: ")
    print("  mul_op(a: Number, b: Number, signed: bool) - Execute MUL op")
    print("  div_op(a: Number, b: Number, signed: bool) - Execute DIV op")
    print("  status()               - Report Output Status")
    print("  test()                 - Run some tests")
    print("  project325_activate()  - Active project")


project325_help()

environment_check()

### THE END
