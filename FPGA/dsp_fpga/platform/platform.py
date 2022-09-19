from amaranth.vendor.intel import IntelPlatform
from amaranth.build import *
from amaranth_boards.resources import *
from amaranth import *
from textwrap import dedent
import os
import subprocess

class DE0NanoPlatform(IntelPlatform):
    device      = "EP4CE22"
    package     = "F17C"
    speed       = "6"
    default_clk = "clk50"
    resources   = [
        Resource("clk50", 0,
            Pins("R8", dir="i"),
            Attrs(io_standard="3.3-V LVTTL")
        ),

        *LEDResources(
            pins="L3 B1 F3 D1 A11 B13 A13 A15",
            attrs=Attrs(io_standard="3.3-V LVTTL")
        ),
        *ButtonResources(
            pins="E1 J15", invert=True,
            attrs=Attrs(io_standard="3.3-V LVTTL")
        ),
        *SwitchResources(
            pins="M15 B9 T8 M1",
            attrs=Attrs(io_standard="3.3-V LVTTL")
        ),
        SDRAMResource(0,
            clk="R4", cke="L7", cs_n="P6", we_n="C2", ras_n="L2", cas_n="L1",
            ba="M6 M7", a="L4 N1 N2 P1 R1 T6 N8 T7 P8 M8 N6 N5 P2",
            dq="K1 N3 P3 R5 R3 T3 T2 T4 R7 J1 J2 K2 K5 L8 G1 G2", dqm="T5 R6",
            attrs=Attrs(io_standard="3.3-V LVCMOS")
        ),
        UARTResource(0,
            rx = 'B4', tx = 'B5',
            attrs=Attrs(io_standard="3.3-V LVTTL")
        ),

        Resource('eeprom', 0,
            Subsignal('scl', Pins('F2', dir = 'io')),
            Subsignal('sda', Pins('F1', dir = 'io')),
            Attrs(io_standard="3.3-V LVTTL")
        ),

        Resource('adc', 0,
            Subsignal('cs_n', Pins('A10', dir = 'o')),
            Subsignal('din' , Pins('B10', dir = 'o')),
            Subsignal('dout', Pins('A9',  dir = 'i')),
            Subsignal('sclk', Pins('B14', dir = 'o')),
            Attrs(io_standard = "3.3-V LVCMOS")
        ),

        Resource('accel', 0,
            Subsignal('sclk', Pins('F2', dir = 'io')),
            Subsignal('sdat', Pins('F1', dir = 'io')),
            Subsignal('int' , Pins('M2', dir = 'i' )),
            Subsignal('cs_n', Pins('G5', dir = 'o' )),
            Attrs(io_standard="3.3-V LVTTL")
        ),

        Resource('display', 0,
            Subsignal('din' , Pins('GPIO_018', dir = 'o', conn = ('j', 0))),
            Subsignal('sclk', Pins('GPIO_022', dir = 'o', conn = ('j', 0))),
            Subsignal('cs_n', Pins('GPIO_020', dir = 'o', conn = ('j', 0))),
            Attrs(io_standard="3.3-V LVTTL")
        )
    ]
    connectors  = [
        Connector("j", 0,
            {
                'GPIO_0_IN0' :  'A8', 'GPIO_00'  :  'D3', 'GPIO_0_IN1' :  'B8',
                'GPIO_01'    :  'C3', 'GPIO_02'  :  'A2', 'GPIO_03'    :  'A3',
                'GPIO_04'    :  'B3', 'GPIO_05'  :  'B4', 'GPIO_06'    :  'A4',
                'GPIO_07'    :  'B5', 'GPIO_08'  :  'A5', 'GPIO_09'    :  'D5',
                'GPIO_010'   :  'B6', 'GPIO_011' :  'A6', 'GPIO_012'   :  'B7',
                'GPIO_013'   :  'D6', 'GPIO_014' :  'A7', 'GPIO_015'   :  'C6',
                'GPIO_016'   :  'C8', 'GPIO_017' :  'E6', 'GPIO_018'   :  'E7',
                'GPIO_019'   :  'D8', 'GPIO_020' :  'E8', 'GPIO_021'   :  'F8',
                'GPIO_022'   :  'F9', 'GPIO_023' :  'E9', 'GPIO_024'   :  'C9',
                'GPIO_025'   :  'D9', 'GPIO_026' : 'E11', 'GPIO_027'   : 'E10',
                'GPIO_028'   : 'C11', 'GPIO_029' : 'B11', 'GPIO_030'   : 'A12',
                'GPIO_031'   : 'D11', 'GPIO_032' : 'D12', 'GPIO_033'   : 'B12',
            }
        ),
        Connector("j", 1,
            {
                'GPIO_1_IN0' :  'T9', 'GPIO_10'  : 'F13', 'GPIO_1_IN1' :  'R9',
                'GPIO_11'    : 'T15', 'GPIO_12'  : 'T14', 'GPIO_13'    : 'T13',
                'GPIO_14'    : 'R13', 'GPIO_15'  : 'T12', 'GPIO_16'    : 'R12',
                'GPIO_17'    : 'T11', 'GPIO_18'  : 'T10', 'GPIO_19'    : 'R11',
                'GPIO_110'   : 'P11', 'GPIO_111' : 'R10', 'GPIO_112'   : 'N12',
                'GPIO_113'   :  'P9', 'GPIO_114' :  'N9', 'GPIO_115'   : 'N11',
                'GPIO_116'   : 'L16', 'GPIO_117' : 'K16', 'GPIO_118'   : 'R16',
                'GPIO_119'   : 'L15', 'GPIO_120' : 'P15', 'GPIO_121'   : 'P16',
                'GPIO_122'   : 'R14', 'GPIO_123' : 'N16', 'GPIO_124'   : 'N15',
                'GPIO_125'   : 'P14', 'GPIO_126' : 'L14', 'GPIO_127'   : 'N14',
                'GPIO_128'   : 'M10', 'GPIO_129' : 'L13', 'GPIO_130'   : 'J16',
                'GPIO_131'   : 'K15', 'GPIO_132' : 'J13', 'GPIO_133'   : 'J14',
            }
        )
    ]

    def toolchain_program(self, products, name):
        quartus_pgm = os.environ.get("QUARTUS_PGM", "quartus_pgm")
        with products.extract("{}.sof".format(name)) as bitstream_filename:
            subprocess.check_call([quartus_pgm, "--haltcc", "--mode", "JTAG",
                                   "--operation", "P;" + bitstream_filename])

    @staticmethod
    def get_pll(ifreq, ofreq, i_clk, o_clk, rst_n):

        b, d = float(ofreq / ifreq).as_integer_ratio()
        return Instance(
            'altclklock',

            p_OPERATION_MODE = "NORMAL",
            p_INCLOCK_PERIOD = int(1e12 / ifreq),
            p_CLOCK0_BOOST   = b,
            p_CLOCK0_DIVIDE  = d,

            i_inclock        = i_clk,
            i_inclocken      = Const(1, 1),

            o_clock0         = o_clk,
            o_locked         = rst_n,
        )

    @staticmethod
    def get_clkbuf(inclk, outclk):
        return Instance(
            'altclkctrl',
            p_WIDTH_CLKSELECT  = 1,
            p_NUMBER_OF_CLOCKS = 1,

            i_clkselect        = Const(0, 1),
            i_ena              = Const(1, 1),
            i_inclk            = inclk,
            o_outclk           = outclk
        )

    @staticmethod
    def change_keep(file):
        res = []
        last = False

        for line in file.splitlines():
            if line.strip() == '(* keep = "true" *)':
                last = True

            elif last:
                res.append(line[:line.find(';')] + " /* synthesis keep */ ;")
                last = False

            else:
                res.append(line)

        return '\n'.join(res)

    def prepare(self, elaboratable, name, **kwargs):
        plan = super().prepare(elaboratable, name, **kwargs)

        plan.files[f'{name}.v']   = self.change_keep(plan.files[f'{name}.v'])
        plan.files[f'{name}.sdc'] += \
            dedent(
                """
                derive_pll_clocks -create_base_clocks
                derive_clock_uncertainty
                """
            )

        return plan

    class SysClk(Elaboratable):
        def __init__(self, pin, ifreq, ofreq):
            self.ifreq   = ifreq
            self.ofreq   = ofreq
            self.pin     = pin

            self.sys_clk = Signal()
            self.sys_rst = Signal()

        def elaborate(self, platform):
            m = Module()

            sys_rst_n = Signal()

            m.submodules.clk_ctrl = DE0NanoPlatform.get_pll(
                ifreq = self.ifreq,
                ofreq = self.ofreq,
                i_clk = self.pin,
                o_clk = self.sys_clk,
                rst_n = sys_rst_n
            )
            platform.add_clock_constraint(self.sys_clk, self.ofreq)

            m.d.comb += self.sys_rst.eq(~sys_rst_n)

            return m

    @staticmethod
    def program_nvm(sof_file):
        import tempfile

        quartus_cpf = os.environ.get("QUARTUS_CPF", "quartus_cpf")
        quartus_pgm = os.environ.get("QUARTUS_PGM", "quartus_pgm")

        with tempfile.NamedTemporaryFile() as tmp:
            jicfile = tmp.name + '.jic'

            print('Generating .jic file...')
            subprocess.check_call([quartus_cpf, "--convert", "--device", "EPCS64",
                                   "--sfl_device", "EP4CE22", sof_file,  jicfile])

            print('Programming nvm...')
            subprocess.check_call([quartus_pgm,   "--mode",   "JTAG",
                                   "--operation", "IBPV;" + jicfile])

            print('Done')