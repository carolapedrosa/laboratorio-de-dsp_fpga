from amaranth import *

class KernelFilter(Elaboratable):
    def __init__(self, h, w, kernel_size, timeout, domain = 'sync'):
        self.h = h
        self.w = w
        self.kernel_size = kernel_size
        self.timeout = timeout
        self.domain  = domain

        assert h < 2**16 - kernel_size//2, "Maximum image size excedeed"
        assert w < 2**16 - kernel_size//2, "Maximum image size excedeed"
        assert kernel_size%2, "Kernel size must be odd"

        self.sink   = Record([('data', 8), ('valid', 1), ('ready', 1)])
        self.source = Record([('data', signed(24)), ('valid', 1), ('ready', 1)])

    def elaborate(self, platform):
        m = Module()
        sync = m.d[self.domain]

        maxh  = self.h + (self.kernel_size - 1)
        maxw  = self.w + (self.kernel_size - 1)
        halfk = self.kernel_size // 2

        mem = Memory(width = 8, depth = maxh * maxw)
        m.submodules.mrp = mrp = mem.read_port(domain = self.domain)
        m.submodules.mwp = mwp = mem.write_port(domain = self.domain)

        memk = Memory(width = 16, depth = self.kernel_size**2)
        m.submodules.krp = krp = memk.read_port(domain = self.domain)
        m.submodules.kwp = kwp = memk.write_port(domain = self.domain)
        # kernel    = Array([Signal(signed(16), name = f'k{i}') for i in range(self.kernel_size**2)])

        addr      = Signal(range(self.kernel_size**2))
        curr      = Signal(signed(len(self.source.data)))
        high      = Signal()
        cntr      = Signal(range(self.timeout))

        row       = Signal(range(maxh))
        col       = Signal(range(maxw))
        krow      = Signal(range(self.kernel_size))
        kcol      = Signal(range(self.kernel_size))
        nxtrow    = Signal(range(maxh))
        nxtcol    = Signal(range(maxw))
        watchrow  = Signal(range(maxh))
        watchol   = Signal(range(maxw))
        nxt_mrp   = Signal(range(maxh * maxw))
        madd      = Signal(signed(len(self.source.data)))

        h         = Signal(range(maxh))
        w         = Signal(range(maxw))
        k         = Signal(range(self.kernel_size))
        currk     = Signal(8)

        m.d.comb  += [
            nxtrow      .eq(Mux(col >= w - 1, row + 1, row)),
            nxtcol      .eq(Mux(col >= w - 1, 0, col + 1)),
            watchrow    .eq(row + krow - halfk),
            watchol     .eq(col + kcol + 1 - halfk),
            nxt_mrp     .eq((nxtrow - halfk)*w + (nxtcol - halfk)),
            # madd        .eq(curr + kernel[addr] * Cat(mrp.data, Const(0, 8))),
            madd        .eq(curr + krp.data.as_signed() * Cat(mrp.data, Const(0, 8))),
        ]
        sync      += [
            kwp.en      .eq(0),
            kwp.addr    .eq(0),
        ]

        with m.If(self.source.ready):
            sync += self.source.valid.eq(0)

        def check_timeout():
            sync = m.d[self.domain]
            with m.If(cntr >= self.timeout - 1):
                m.next = 'KERNEL'
                sync += cntr.eq(0)

        def iter_colrow(col, row, w):
            sync = m.d[self.domain]
            with m.If(col < w - 1):
                sync += col.eq(col + 1)
            with m.Else():
                sync += col.eq(0), row.eq(row + 1)

        def iter_filter():
            with m.If((row == h - 1) & (col == w - 1)):
                m.next = 'KERNEL'
            with m.Else():
                m.d.comb += mrp.addr.eq(nxt_mrp)
                iter_colrow(col, row, w)

        with m.FSM(reset = 'KERNEL', domain = self.domain):
            with m.State('KERNEL'):
                m.d.comb += self.sink.ready.eq(1)
                sync += [
                    row      .eq(0),
                    col      .eq(0),
                    krow     .eq(0),
                    kcol     .eq(0),
                    mwp.addr .eq(0),
                    cntr     .eq(0),
                    addr     .eq(0),
                    high     .eq(0),
                ]

                with m.If(self.sink.valid):
                    sync += k.eq(self.sink.data | Const(1, 1))
                    m.next = 'LOAD'
            
            with m.State('LOAD'):
                m.next = 'COEFS'

            with m.State('COEFS'):
                with m.If(
                    (krow < (self.kernel_size - k)[1:]) |
                    (krow >= (k + self.kernel_size)[1:]) |
                    (kcol < (self.kernel_size - k)[1:]) |
                    (kcol >= (k + self.kernel_size)[1:])
                ):
                    sync += [
                        high        .eq(0),
                        addr        .eq(addr + 1),
                        kwp.en      .eq(1),
                        kwp.data    .eq(0),
                    ]
                    iter_colrow(kcol, krow, self.kernel_size)
                    with m.If(addr >= self.kernel_size**2 - 1):
                        m.next = 'SIZE'
                        sync += addr.eq(0), kcol.eq(0), krow.eq(0)

                with m.Else():
                    m.d.comb += self.sink.ready.eq(1)
                    with m.If(self.sink.valid):
                        sync += [
                            addr.eq(addr + high),
                            high.eq(~high),
                            cntr.eq(0),
                        ]
                        with m.If(high):
                            sync += [
                                kwp.en.eq(1),
                                kwp.addr.eq(self.kernel_size**2 - addr - 1),
                                kwp.data.eq(Cat(currk, self.sink.data)),
                            ]
                        with m.Else():
                            sync += currk.eq(self.sink.data)

                        with m.If(high):
                            iter_colrow(kcol, krow, self.kernel_size)
                            with m.If(addr >= self.kernel_size**2 - 1):
                                m.next = 'SIZE'
                                sync += addr.eq(0), kcol.eq(0), krow.eq(0)
                
                    with m.Else():
                        sync += cntr.eq(cntr + 1)

                check_timeout()

            with m.State('SIZE'):
                m.d.comb += self.sink.ready.eq(1)
                with m.If(self.sink.valid):
                    sync += [
                        addr.eq(addr + 1),
                        Cat(h, Signal(16-len(h)), w, Signal(16-len(w))).word_select(addr[:2], 8).eq(self.sink.data),
                        cntr.eq(0),
                    ]
                    with m.If(addr == 3):
                        sync += addr.eq(0)
                        m.next = 'PAD'
                
                with m.Else():
                    sync += cntr.eq(cntr + 1)
                
                check_timeout()

            with m.State('PAD'):
                sync += [
                    h.eq(h + (self.kernel_size - 1)),
                    w.eq(w + (self.kernel_size - 1)),
                ]
                m.next = 'IMAGE'

            with m.State('IMAGE'):
                with m.If(
                    (row < halfk) |
                    (row >= h - halfk) |
                    (col < halfk) |
                    (col >= w - halfk)
                ):
                    m.d.comb += [
                        mwp.en  .eq(1),
                        mwp.data.eq(0),
                    ]
                    with m.If(mwp.addr >= h * w - 1):
                        m.next = 'FILTER'
                        sync += mwp.addr.eq(0), col.eq(0), row.eq(0)
                    with m.Else():
                        sync += mwp.addr.eq(mwp.addr + 1)
                        iter_colrow(col, row, w)

                with m.Else():
                    m.d.comb += self.sink.ready.eq(1)
                    with m.If(self.sink.valid):
                        m.d.comb += [
                            mwp.en  .eq(1),
                            mwp.data.eq(self.sink.data),
                        ]
                        sync += [
                            cntr.eq(0),
                            mwp.addr.eq(mwp.addr + 1),
                        ]
                        iter_colrow(col, row, w)

                    with m.Else():
                        sync += cntr.eq(cntr + 1)

                    check_timeout()

            with m.State('FILTER'):
                m.d.comb += krp.addr.eq(addr)

                with m.If(~self.source.valid | self.source.ready):
                    sync += cntr.eq(0)
                    with m.If(
                        (row < halfk) | 
                        (row >= h - halfk) |
                        (col < halfk) | 
                        (col >= w - halfk)
                    ):
                        sync += addr.eq(0), krow.eq(0), kcol.eq(0)
                        m.d.comb += krp.addr.eq(0)
                        iter_filter()

                    with m.Else():
                        sync += curr.eq(madd)

                        with m.If(addr >= self.kernel_size**2 - 1):
                            sync += [
                                addr                .eq(0),
                                curr                .eq(0),
                                kcol                .eq(0),
                                krow                .eq(0),
                                self.source.valid   .eq(1),
                                self.source.data    .eq(madd),
                            ]
                            m.d.comb += [
                                krp.addr            .eq(0),
                            ]
                            iter_filter()

                        with m.Else():
                            sync += addr.eq(addr + 1)
                            m.d.comb += krp.addr.eq(addr + 1)
                            iter_colrow(kcol, krow, self.kernel_size)

                            with m.If(kcol >= self.kernel_size - 1):
                                m.d.comb += mrp.addr.eq((watchrow + 1) * w + col - halfk)
                            with m.Else():
                                m.d.comb += mrp.addr.eq(watchrow * w + watchol)

                with m.Else():
                    sync += cntr.eq(cntr + 1)

                check_timeout()

        return m
