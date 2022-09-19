from amaranth import *

class RampGenerator(Elaboratable):
    def __init__(self, width, double, domain = 'sync'):
        self.domain = domain
        self.double = double

        self.out    = Signal(width)
        self.step   = Signal()

    def elaborate(self, platform):
        m = Module()
        sync = m.d[self.domain]

        if self.double:
            step = Signal(signed(len(self.out)), reset = 1)
        else:
            step = Const(1, 1)

        tmp_sum = Signal.like(self.out)
        m.d.comb += tmp_sum.eq(self.out + step)

        with m.If(self.step):
            sync += self.out.eq(tmp_sum)

            if self.double:
                with m.If(tmp_sum.all() | ~tmp_sum.any()):
                    sync += step.eq(~step + 1)

        return m