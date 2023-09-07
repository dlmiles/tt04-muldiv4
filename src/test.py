import cocotb
from cocotb.clock import Clock
from cocotb.binary import BinaryValue
from cocotb.triggers import RisingEdge, FallingEdge, Timer, ClockCycles


def report(dut, ui_in, uio_in):
    uio_out = dut.uio_out.value
    uo_out = dut.uo_out.value

    s_eover = 'EOVER' if(uio_out.is_resolvable and uio_out & 0x10) else ''
    s_ediv0 = 'EDIV0' if(uio_out.is_resolvable and uio_out & 0x20) else ''

    if uio_in & 0x40:
        opsigned = True
        s_ounsign = 'SIGNED'
    else:
        opsigned = False
        s_ounsign = 'UNSIGN'

    if uio_in & 0x80:
        s_omuldiv = 'DIV'
        dend = ui_in & 0xf
        dsor = (ui_in >> 4) & 0xf
        q = int(uo_out & 0xf)
        r = int((uo_out >> 4) & 0xf)
        if opsigned:
            dend = dend if(dend < 8) else dend - 16
            dsor = dsor if(dsor < 8) else dsor - 16
            q = q if(q < 8) else q - 16
            r = r if(r < 8) else r - 16
        dut._log.info(f"in={str(ui_in)} {str(uio_in)}  out={str(uo_out)} {str(uio_out)}   {s_omuldiv} {s_ounsign} {dend:4d} / {dsor:4d} = {q:3d} r {r:3d} {s_ediv0} {s_eover}")
    else:
        s_omuldiv = 'MUL'
        a = ui_in & 0xf
        b = (ui_in >> 4) & 0xf
        p = int(uo_out)
        if opsigned:
            a = a if(a < 8) else a - 16
            b = b if(b < 8) else b - 16
            p = p if(p < 128) else p - 256
        dut._log.info(f"in={str(ui_in)} {str(uio_in)}  out={str(uo_out)} {str(uio_out)}   {s_omuldiv} {s_ounsign} {a:4d} x {b:4d} = {p:5d}")


@cocotb.test()
async def test_muldiv(dut):
    dut._log.info("start")
    clock = Clock(dut.clk, 10, units="us")
    cocotb.start_soon(clock.start())

    await ClockCycles(dut.clk, 2)	# show X

    # ena=0 state
    dut.ena.value = 0
    dut.rst_n.value = 0
    dut.clk.value = 0
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    await ClockCycles(dut.clk, 2)	# show muted inputs ena=0

    dut._log.info("ena (active)")
    dut.ena.value = 1		# ena=1
    await ClockCycles(dut.clk, 2)

    dut._log.info("reset (inactive)")
    dut.rst_n.value = 1		# come out of reset
    await ClockCycles(dut.clk, 2)

    # MULU MULS DIVU DIVS
    for uio_in_mode in [0x00, 0x40, 0x80, 0xc0]:
        for uio_in in range(0x3f+1):
            uio_in |= uio_in_mode
            dut.uio_in.value = uio_in

            for ui_in in range(255+1):
                dut.ui_in.value = ui_in

                await ClockCycles(dut.clk, 2)
                report(dut, BinaryValue(ui_in, bigEndian=False, n_bits=8), BinaryValue(uio_in, bigEndian=False, n_bits=8))
