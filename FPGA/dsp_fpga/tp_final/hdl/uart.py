from amaranth import *
from amaranth.lib.cdc import FFSynchronizer


def _compute_parity_bit(data, parity, m):
    res = Signal()
    with m.Switch(parity):
        with m.Case(1): m.d.comb += res.eq(~data.xor())
        with m.Case(3): m.d.comb += res.eq(data.xor())
        with m.Case(5): m.d.comb += res.eq(1)
        with m.Default(): m.d.comb += res.eq(0)

    return res

class AsyncSerialRX(Elaboratable):

    def __init__(self, pins, div_rst, domain = 'sync'):
        self.parity = Signal(3)
        self.bits = Signal(2)
        self.divisor = Signal(32, reset = div_rst)
        self.stop = Signal()

        self.data = Signal(8)
        self.err  = Record([
            ("overflow", 1),
            ("frame",    1),
            ("parity",   1),
            ("break_cond", 1),
        ])
        self.rdy  = Signal()
        self.ack  = Signal()

        self.i    = Signal(reset=1)

        self._pins = pins

        self.domain = domain
        self.do_break = Signal()

    def elaborate(self, platform):
        m = Module()
        sync = m.d[self.domain]

        timer = Signal.like(self.divisor)
        shreg = Signal(12)
        bitno = Signal(range(len(shreg)))

        shreg = {
            'start' : Signal(name = 'start'),
            'data' : Signal(8, name = 'data'),
            'parity' : Signal(name = 'parity'),
            'stop' : Signal(name = 'stop'),
        }

        if self._pins is not None:
            m.submodules.ff = FFSynchronizer(self._pins.rx.i, self.i, reset=1)

        with m.FSM(reset = 'IDLE', domain = self.domain) as fsm:
            with m.State("IDLE"):
                with m.If(~self.i):
                    sync += [
                        bitno.eq(5 + self.bits),
                        timer.eq(self.divisor[1:] - 1),
                    ]
                    m.next = "START"

            with m.State('START'):
                with m.If(timer != 0):
                    sync += timer.eq(timer - 1)
                with m.Else():
                    sync += [
                        timer.eq(self.divisor - 1),
                        shreg['start'].eq(self.i)
                    ]
                    m.next = 'DATA'

            with m.State('DATA'):
                with m.If(timer != 0):
                    sync += timer.eq(timer - 1)
                with m.Else():
                    sync += [
                        timer.eq(self.divisor - 1),
                        shreg['data'].eq(Cat(shreg['data'][1:], self.i)),
                        bitno.eq(bitno - 1),
                    ]
                    with m.If(bitno == 1):
                        with m.If(self.parity): m.next = 'PARITY'
                        with m.Else(): m.next = 'STOP'

            with m.State('PARITY'):
                with m.If(timer != 0):
                    sync += timer.eq(timer - 1)
                with m.Else():
                    sync += [
                        timer.eq(self.divisor - 1),
                        shreg['parity'].eq(self.i),
                    ]
                    m.next = 'STOP'

            with m.State('STOP'):
                with m.If(timer != 0):
                    sync += timer.eq(timer - 1)
                with m.Else():
                    sync += [
                        timer.eq(0),
                        shreg['stop'].eq(self.i),
                    ]
                    m.next = 'DONE'

            with m.State("DONE"):
                with m.If(self.ack):
                    sync += [
                        self.data.eq(shreg['data'].bit_select(3 - self.bits, 8)),
                        self.err.frame .eq(shreg['start'] | ~shreg['stop']),
                        self.err.parity.eq(self.parity[0] & (shreg['parity'] != _compute_parity_bit(shreg['data'], self.parity, m))),
                        self.err.break_cond.eq(~shreg['start'] & ~shreg['stop'] & ~shreg['data'] & (~self.parity[0] | ~shreg['parity'])),
                        *[shreg[k].eq(0) for k in shreg],
                    ]
                sync += self.err.overflow.eq(~self.ack)
                m.next = "IDLE"

        with m.If(self.ack):
            sync += self.rdy.eq(fsm.ongoing("DONE"))

        return m


class AsyncSerialTX(Elaboratable):
    def __init__(self, pins, div_rst, domain = 'sync'):
        self.parity = Signal(3)
        self.stop = Signal()
        self.bits = Signal(2)

        self.divisor = Signal(32, reset = div_rst)

        self.data = Signal(8)
        self.rdy  = Signal()
        self.ack  = Signal()

        self.o    = Signal(reset=1)

        self._pins = pins
        self.domain = domain

        self.do_break = Signal()

    def elaborate(self, platform):
        m = Module()
        sync = m.d[self.domain]

        timer = Signal(range(self.divisor)) if isinstance(self.divisor, int) else Signal.like(self.divisor)
        # shreg = Signal(12)
        bitno = Signal(range(12))

        m.d.comb += self._pins.tx.o.eq(self.o & ~self.do_break)

        shreg = {
            'data'  : Signal(8, name = 'data'),
            'parity' : Signal(name = 'parity'),
        }

        with m.FSM(reset = 'IDLE', domain = self.domain):
            with m.State('IDLE'):
                m.d.comb += self.rdy.eq(1)
                with m.If(self.ack):
                    sync += [
                        shreg['data'].eq(self.data),
                        shreg['parity'].eq(_compute_parity_bit(self.data, self.parity, m)),
                        timer.eq(self.divisor - 1),
                    ]
                    m.next = 'START'

            with m.State('START'):
                with m.If(timer != 0): sync += timer.eq(timer - 1)
                with m.Else():
                    sync += [
                        self.o.eq(0),
                        timer.eq(self.divisor - 1),
                        bitno.eq(5 + self.bits),
                    ]
                    m.next = "DATA"

            with m.State('DATA'):
                with m.If(timer != 0): sync += timer.eq(timer - 1)
                with m.Else():
                    sync += [
                        Cat(self.o, shreg['data']).eq(shreg['data']),
                        timer.eq(self.divisor - 1),
                        bitno.eq(bitno - 1),
                    ]
                    with m.If(bitno == 1):
                        with m.If(self.parity[0]): m.next = "PARITY"
                        with m.Else(): m.next = 'STOP'

            with m.State('PARITY'):
                with m.If(timer != 0): sync += timer.eq(timer - 1)
                with m.Else():
                    sync += [
                        self.o.eq(shreg['parity']),
                        timer.eq(self.divisor - 1),
                    ]
                    m.next = 'STOP'

            with m.State('STOP'):
                with m.If(timer != 0): sync += timer.eq(timer - 1)
                with m.Else():
                    sync += [
                        self.o.eq(Const(1, 1)),
                        timer.eq(self.divisor - 1),
                    ]
                    with m.If(self.stop & ~bitno.any()): sync += bitno.eq(bitno + 1)
                    with m.Else():
                        sync += bitno.eq(0)
                        m.next = 'IDLE'

        return m


class AsyncSerial(Elaboratable):
    def __init__(self, pins, div_rst, domain = 'sync'):
        self.rx = AsyncSerialRX(pins, div_rst, domain = domain)
        self.tx = AsyncSerialTX(pins, div_rst, domain = domain)

    def elaborate(self, platform):
        m = Module()
        m.submodules.rx = self.rx
        m.submodules.tx = self.tx
        return m

class Uart(Elaboratable):
    def __init__(self, pins, div_rst, domain = 'sync'):
        self.pins = pins
        self.div_rst = div_rst
        self.domain = domain

        self.sink = Record([('data', 8), ('valid', 1), ('ready', 1)])
        self.source = Record([('data', 8), ('valid', 1), ('ready', 1)])

        self.config = Record([
            ('divisor', 32),
            ('stop', 1),
            ('parity', 3),
            ('bits', 2),
            ('do_break', 1)
        ])

        self.tx_rdy = Signal()

    def elaborate(self, platform):
        m = Module()
        sync = m.d[self.domain]

        m.submodules.uart = uart = DomainRenamer({'sync' : self.domain})(
            AsyncSerial(pins=self.pins, div_rst = self.div_rst)
        )

        with m.If(self.source.valid & self.source.ready):
            sync += self.source.valid.eq(0)
        with m.If(uart.rx.rdy):
            sync += [
                self.source.data.eq(uart.rx.data),
                self.source.valid.eq(1),
            ]

        m.d.comb += [
            self.tx_rdy.eq(uart.tx.rdy),
            uart.tx.data.eq(self.sink.data),
            uart.tx.ack.eq(self.sink.valid),
            self.sink.ready.eq(uart.tx.rdy),
            uart.rx.ack.eq(1),

            *[
                getattr(getattr(uart, dir), name).eq(getattr(self.config, name))
                for name in self.config.fields.keys() for dir in ['tx', 'rx']
            ]
        ]

        return m
