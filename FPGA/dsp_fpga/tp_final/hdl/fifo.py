from amaranth import *
from amaranth.lib.fifo import FIFOInterface
from amaranth._utils import log2_int
from math import ceil, log2

class SyncFifo(Elaboratable, FIFOInterface):
    def __init__(self, *, width, depth, domain = 'sync', exact_depth=False):
        if depth != 0:
            try:
                depth_bits = log2_int(depth, need_pow2=exact_depth)
                depth = 1 << depth_bits
            except ValueError:
                raise ValueError("SyncFIFO only supports depths that are powers of 2; requested "
                                 "exact depth {} is not"
                                 .format(depth)) from None
        else:
            depth_bits = 0
        super().__init__(width=width, depth=depth, fwft=True)

        self.r_rst = Signal()
        self.domain = domain
        self._ctr_bits = depth_bits + 1
        self.level = Signal(range(self.depth + 1))

    def elaborate(self, platform):
        m = Module()
        sync = m.d[self.domain]

        if self.depth == 0:
            m.d.comb += [
                self.w_rdy.eq(0),
                self.r_rdy.eq(0),
            ]
            return m

        do_write = self.w_rdy & self.w_en
        do_read  = self.r_rdy & self.r_en

        produce_w_bin = Signal(self._ctr_bits)
        produce_w_nxt = Signal(self._ctr_bits)

        consume_r_bin = Signal(self._ctr_bits, reset_less = True)
        consume_r_nxt = Signal(self._ctr_bits)

        produce_r_bin = Signal(self._ctr_bits)

        wen = Signal()
        w_full  = Signal()
        r_empty = Signal()
        m.d.comb += [
            w_full.eq(
                ((self.level + wen) >= self.depth)
            ),
            r_empty.eq(
                ~self.level.any()
            )
        ]
        storage = Memory(width = self.width, depth = self.depth)
        w_port  = m.submodules.w_port = storage.write_port(domain = self.domain)
        r_port  = m.submodules.r_port = storage.read_port (domain = self.domain,
                                                           transparent = False)
        m.d.comb += [
            w_port.addr .eq(produce_w_bin[:-1]),
            w_port.data .eq(self.w_data),
            w_port.en   .eq(do_write),
            self.w_rdy  .eq(~w_full),
            r_port.addr .eq(consume_r_nxt[:-1]),
            self.r_data .eq(r_port.data),
            r_port.en   .eq(1),
            self.r_rdy  .eq(~r_empty),

            produce_w_nxt.eq(produce_w_bin + do_write),
            consume_r_nxt.eq(consume_r_bin + do_read),
        ]

        sync += [
            produce_w_bin.eq(produce_w_nxt),
            consume_r_bin.eq(consume_r_nxt),
            produce_r_bin.eq(produce_w_nxt),

            wen.eq(do_write),
            self.level.eq(self.level + wen - do_read),
        ]

        w_rst = ResetSignal(domain = self.domain, allow_reset_less = True)
        r_rst = Signal(reset = 1)

        newdom = 'newdom'
        m.domains += ClockDomain(newdom, local = True, async_reset = True)
        m.d.comb += ClockSignal(newdom).eq(ClockSignal(self.domain))
        m.d.comb += ResetSignal(newdom).eq(w_rst)
        m.d[newdom] += r_rst.eq(0)

        with m.If(r_rst):
            m.d.comb += r_empty.eq(1)
            sync += [
                consume_r_bin.eq(produce_w_nxt),
                self.r_rst.eq(1),
            ]
        with m.Else():
            sync += self.r_rst.eq(0)

        return m


class Fifo(Elaboratable):
    def __init__(self, payload, depth, domain = 'sync'):
        self.payload = payload
        self.sink    = Record([('valid', 1), ('ready', 1)] + payload)
        self.source  = Record([('valid', 1), ('ready', 1)] + payload)
        self.depth   = depth
        self.domain  = domain

        self.level = Signal(range(int(2**ceil(log2(depth)) + 1)))

    def elaborate(self, platform):
        m = Module()
        width = sum(v for k, v in self.payload)

        m.submodules.fifo = afifo = SyncFifo(width = width, depth = self.depth, domain = self.domain)
        m.d.comb += self.level.eq(afifo.level)

        m.d.comb += [
            self.sink.ready.eq(afifo.w_rdy),
            afifo.w_en.eq(self.sink.valid),
            self.source.valid.eq(afifo.r_rdy),
            afifo.r_en.eq(self.source.ready),
        ]

        m.d.comb += [
            afifo.w_data.eq(Cat(self.sink[key] for key, _ in self.payload)),
            Cat(self.source[key] for key, _ in self.payload).eq(afifo.r_data),
        ]

        return m
