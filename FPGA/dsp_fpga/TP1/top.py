from amaranth import *
import os
from dsp_fpga.platform.platform import DE0NanoPlatform
import argparse

if __name__ == '__main__':

    assert 'QUARTUS_PATH' in os.environ, "Please specify path for quartus executables"

    parser = argparse.ArgumentParser()
    parser.add_argument('--vhdl', required = False, action = 'store_true', default = False)
    parser.add_argument('--no-program', required = False, action = 'store_true', default = False)
    parser.add_argument('--nvm', required = False, action = 'store_true', default = False)
    args = parser.parse_args()

    m = Module()
    sync = m.d['sync']

    platform = DE0NanoPlatform()
    _clkfreq = int(50e6)
    clkfreq  = int(100e6)

    m.submodules.pll = pll = platform.SysClk(
        pin = platform.request('clk50', 0),
        ifreq = _clkfreq,
        ofreq = clkfreq,
    )

    m.domains += ClockDomain('sync')
    m.d.comb  += [
        ClockSignal('sync').eq(pll.sys_clk),
        ResetSignal('sync').eq(pll.sys_rst),
    ]

    leds = Cat(platform.request('led', i) for i in range(8))

    if args.vhdl:
        step    = Signal()
        duty    = Signal(8)
        freqdiv = Signal()
        m.submodules.pwm = Instance(
            'PWM',

            p_duty_bits = 8,
            p_freq      = int(100e3),
            p_sys_freq  = int(100e6),
            p_phases    = len(leds),

            i_clk       = ClockSignal('sync'),
            i_rst_n     = ~ResetSignal('sync'),
            i_duty      = duty,
            i_en        = freqdiv,

            o_pwm       = leds,
            o_pwm_n     = Signal(len(leds)),
        )
        m.submodules.ramp = Instance(
            'RampGenerator',

            p_width  = 8,
            p_double = 1,

            i_clk    = ClockSignal('sync'),
            i_rst_n  = ~ResetSignal('sync'),
            i_step   = step,

            o_ramp   = duty,
        )
        m.submodules.freqdiv = Instance(
            'Freqdiv',

            p_div_half = (2**20 // 2),

            i_clk      = ClockSignal('sync'),
            i_rst_n    = ~ResetSignal('sync'),

            o_freqdiv  = freqdiv,
            o_re       = step,
        )

        from glob import glob

        sources = glob(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'vhdl', '*.vhd'))

        for file in sources:
            with open(file, 'r') as f:
                platform.add_file(file, f.read())

    else:
        from dsp_fpga.TP1.pwm import PWM
        m.submodules.pwm = pwm = PWM(
            duty_bits = 8,
            phases = len(leds),
            freq = 100e3,
            sys_freq = clkfreq,
            domain = 'sync',
        )

        from dsp_fpga.TP1.ramp import RampGenerator
        m.submodules.ramp = ramp = RampGenerator(
            width = 8,
            double = True,
            domain = 'sync',
        )

        from dsp_fpga.TP1.freqdiv import Freqdiv
        m.submodules.freqdiv = freqdiv = Freqdiv(
            div_half = (2**20 // 2),
            domain = 'sync',
        )

        sync += [
            ramp.step.eq(freqdiv.out_re),
            pwm.duty.eq(ramp.out),
            pwm.enable.eq(freqdiv.out),
            leds.eq(pwm.output),
        ]

    for name in platform.required_tools + ['quartus_pgm', 'quartus_cpf']:
        os.environ[name.upper()] = os.path.join(os.getenv('QUARTUS_PATH'), name)

    platform.build(m, do_build = True, do_program = not args.no_program)
    if args.nvm:
        platform.program_nvm(os.path.join('build', 'top.sof'))