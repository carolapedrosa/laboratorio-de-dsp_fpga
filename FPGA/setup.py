from setuptools import setup, find_packages
  
setup(
    name='dsp_fpga',
    packages=find_packages('.'),
    install_requires=[
        'markupsafe==2.0.1',
        'amaranth==0.3',
        'amaranth-yosys',
        'amaranth-boards @ git+https://github.com/amaranth-lang/amaranth-boards.git',
        'amaranth-stdio @ git+https://github.com/amaranth-lang/amaranth-stdio.git',
        'cocotb',
        'cocotb_bus',
        'pytest',
    ]
)
