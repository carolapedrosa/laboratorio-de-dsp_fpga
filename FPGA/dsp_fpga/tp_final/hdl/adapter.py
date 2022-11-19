from amaranth import *
from math import ceil, log2

class Adapter(Elaboratable):
    def __init__(self, input_w, output_w, domain = 'sync'):
        i_payload = [('data', input_w)]
        o_payload = [('data', output_w)]

        self.sink   = Record(i_payload + [('valid', 1), ('ready', 1)])
        self.source = Record(o_payload + [('valid', 1), ('ready', 1)])
        self.domain = domain
        self.i_w    = input_w
        self.o_w    = output_w

    def elaborate(self, platform):
        m = Module()
        sync = m.d[self.domain]
        comb = m.d.comb

        sink = self.sink
        source = self.source

        ratio = self.o_w / self.i_w if self.o_w > self.i_w else self.i_w / self.o_w
        assert ratio.is_integer()
        ratio = int(ratio)

        if self.o_w > self.i_w:
            data = Signal(self.o_w)
            cnt  = Signal(ceil(log2(ratio)))

            end = cnt == ratio - 1
            with m.If(source.valid & source.ready):
                sync += [
                    source.valid.eq(0),
                    data.eq(0),
                ]

            with m.If(source.valid):
                comb += source.data.eq(data)

            with m.If(sink.valid & sink.ready):
                sync += data.word_select(cnt, self.i_w).eq(sink.data),
                with m.If(end):
                    sync += [
                        source.valid.eq(1),
                        cnt.eq(0),
                    ]
                with m.Else():
                    sync += cnt.eq(cnt + 1)

            with m.If(~source.valid | source.ready):
                comb += sink.ready.eq(1)

        elif self.o_w < self.i_w:
            data = Signal(self.i_w)
            cnt = Signal(ceil(log2(ratio)))

            comb += source.data.eq(data[0:self.o_w])

            last_part = Signal()

            comb += last_part.eq(0)
            with m.If(source.valid & source.ready):
                sync += [
                    cnt.eq(cnt - 1),
                    data.eq(data >> self.o_w)
                ]

                with m.If(cnt == 0):
                    comb += last_part.eq(1)

                with m.If(last_part):
                    sync += source.valid.eq(0),

            with m.If(sink.valid & sink.ready):
                sync += [
                    cnt.eq(ratio - 1),
                    data.eq(sink.data),
                    source.valid.eq(1),
                ]

            with m.If(~source.valid | (last_part & source.valid & source.ready)):
                comb += sink.ready.eq(1)

        return m
