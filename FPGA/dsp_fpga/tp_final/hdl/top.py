from amaranth import *
import os
from dsp_fpga.platform.platform import DE0NanoPlatform
import argparse
from dsp_fpga.tp_final.hdl.fifo import Fifo
from dsp_fpga.tp_final.hdl.uart import Uart
from dsp_fpga.tp_final.hdl.adapter import Adapter
from dsp_fpga.tp_final.hdl.kernel_filter import KernelFilter
from math import ceil, log2

if __name__ == '__main__':

    assert 'QUARTUS_PATH' in os.environ, "Please specify path for quartus executables"

    parser = argparse.ArgumentParser()
    parser.add_argument('--no-program', required = False, action = 'store_true', default = False)
    parser.add_argument('--nvm', required = False, action = 'store_true', default = False)
    args = parser.parse_args()

    m = Module()
    sync = m.d['sync']

    platform = DE0NanoPlatform()
    _clkfreq = int(50e6)
    clkfreq  = int(50e6)

    # m.submodules.pll = pll = platform.SysClk(
    #     pin = platform.request('clk50', 0),
    #     ifreq = _clkfreq,
    #     ofreq = clkfreq,
    # )

    m.domains += ClockDomain('sync')
    # m.d.comb  += [
    #     ClockSignal('sync').eq(pll.sys_clk),
    #     ResetSignal('sync').eq(pll.sys_rst),
    # ]
    clk = Signal()
    m.d.comb += clk.eq(platform.request('clk50', 0))
    m.d.comb += ClockSignal('sync').eq(clk)
    platform.add_clock_constraint(clk, 50e6)

    m.submodules.kernel = kernel = KernelFilter(
        h           = 200,
        w           = 200,
        kernel_size = 11,
        timeout     = int(2**ceil(log2(clkfreq * 5))),
        domain      = 'sync'
    )

    m.submodules.rfifo = rfifo = Fifo(
        payload = [('data', 8)],
        depth   = 256,
        domain  = 'sync', 
    )
    m.submodules.tfifo = tfifo = Fifo(
        payload = [('data', 8)],
        depth   = 256,
        domain  = 'sync', 
    )
    m.submodules.uart = uart = Uart(
        pins    = platform.request('uart', 0),
        div_rst = int(clkfreq / 230400),
        domain  = 'sync'
    )
    m.submodules.adapter = adapter = Adapter(
        input_w  = len(kernel.source.data),
        output_w = 8,
        domain   = 'sync', 
    )

    leds = Cat(platform.request('led', i) for i in range(8))
    with m.If(uart.source.valid & uart.source.ready):
        sync += leds.eq(uart.source.data)

    def connect(sink, source):
        return [
            source[v].eq(sink[v]) for v in sink.fields.keys() if v != 'ready'
        ] + [sink.ready.eq(source.ready)]

    m.d.comb += [
        uart.config.divisor.eq(int(clkfreq / 230400)),
        uart.config.stop.eq(0),
        uart.config.parity.eq(0),
        uart.config.bits.eq(3),
        uart.config.do_break.eq(0),

        *connect(uart.source,  rfifo.sink),
        *connect(rfifo.source, kernel.sink),

        *connect(kernel.source,  adapter.sink),
        *connect(adapter.source, tfifo.sink),
        *connect(tfifo.source,   uart.sink),
    ]

    for name in platform.required_tools + ['quartus_pgm', 'quartus_cpf']:
        os.environ[name.upper()] = os.path.join(os.getenv('QUARTUS_PATH'), name)

    platform.build(m, do_build = True, do_program = not args.no_program)
    if args.nvm:
        platform.program_nvm(os.path.join('build', 'top.sof'))