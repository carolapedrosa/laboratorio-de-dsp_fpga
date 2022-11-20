# laboratorio-de-dsp_fpga


## Para correr tp_final:


- cd FPGA/dsp_fpga/tp_final/
- pip3 install -r requirements.txt
- python3 main.py


## Para generar (y/o programar) bitfile de FPGA:

- cd FPGA/
- pip3 install -e .
- cd dsp_fpga/tp_final/hdl/
- python3 top.py            # (--help para ayuda de comandos)
