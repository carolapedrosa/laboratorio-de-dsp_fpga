from amaranth import *

class Freqdiv(Elaboratable):
    def __init__(self, div_half, domain = 'sync'):
        self.div    = div_half
        self.domain = domain

        self.out    = Signal()
        self.out_re = Signal()

        assert div_half > 0

    def elaborate(self, platform):
        m = Module()
        sync = m.d[self.domain]

        counter = Signal(range(self.div))

        sync += [
            counter.eq(Mux(counter == self.div - 1, 0, counter + 1)),
            self.out.eq(Mux(counter.any(), self.out, ~self.out)),
            self.out_re.eq(~counter.any()),
        ]

        return m