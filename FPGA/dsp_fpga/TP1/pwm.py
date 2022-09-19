from amaranth import *

class _PWM(Elaboratable):
    def __init__(self, duty_bits, freq, sys_freq, domain = 'sync'):
        self.duty     = Signal(duty_bits)
        self.output   = Signal()
        self.output_n = Signal()
        self.enable   = Signal()

        self.freq     = freq
        self.sys_freq = sys_freq
        self.domain   = domain

    def elaborate(self, platform):
        m = Module()
        sync = m.d[self.domain]

        lim     = int(round(self.sys_freq / self.freq))
        counter = Signal(range(lim))
        out     = Signal()

        with m.If(self.enable):
            sync += [
                counter.eq(Mux(counter == lim - 1, 0, counter + 1)),
                out.eq(counter < ((self.duty * lim) >> len(self.duty))),
                self.output.eq(out),
            ]
        with m.Else():
            sync += [
                counter.eq(0),
                out.eq(0),
                self.output.eq(0),
            ]
        m.d.comb += [
            self.output_n.eq(~self.output),
        ]

        return m

class PWM(Elaboratable):
    def __init__(self, duty_bits, phases, freq, sys_freq, domain = 'sync'):
        self.duty     = Signal(duty_bits)
        self.output   = Signal(phases)
        self.output_n = Signal(phases)
        self.enable   = Signal()

        self.freq     = freq
        self.sys_freq = sys_freq
        self.domain   = domain
        self.phases   = phases

        assert 0 < phases

    def elaborate(self, platform):
        m = Module()
        sync = m.d[self.domain]

        lim = self.sys_freq / self.freq

        for i in range(self.phases):
            delay   = int(round(lim / self.phases * i))
            counter = Signal(range(delay + 1))
            en      = self.enable & (counter >= delay)

            with m.If(self.enable):
                sync += counter.eq(Mux(en, counter, counter + 1))
            with m.Else():
                sync += counter.eq(0)

            m.submodules[f'pwm_{i}'] = pwm = _PWM(
                duty_bits = len(self.duty),
                freq      = self.freq,
                sys_freq  = self.sys_freq,
                domain    = self.domain,
            )

            sync += [
                pwm.duty.eq(self.duty),
                pwm.enable.eq(en),
                self.output[i].eq(pwm.output),
                self.output_n[i].eq(pwm.output_n),
            ]

        return m