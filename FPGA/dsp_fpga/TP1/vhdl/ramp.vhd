library IEEE;
use IEEE.std_logic_1164.all;
use ieee.math_real.all;
use IEEE.numeric_std.all;
use ieee.std_logic_unsigned.all;

entity RampGenerator is
    generic (
        double : integer range 0 to 1 := 0;
        width  : integer := 1
    );
    port(
        rst_n :  in std_logic;
        clk   :  in std_logic;
        step  :  in std_logic;
        ramp  : out std_logic_vector(width - 1 downto 0) := (others => '0')
    );
end;

architecture rtl of RampGenerator is
    constant maxval : integer := 2**width - 1;

    signal stepint  : std_logic_vector(width - 1 downto 0) := (0=>'1', others => '0');
    signal o_tmp    : std_logic_vector(width - 1 downto 0) := (others => '0');
    signal tmp_sum  : std_logic_vector(width - 1 downto 0);

    function i2sv(
        i      : in integer;
        length : in integer := width
    ) return std_logic_vector is
        begin
            return std_logic_vector(to_unsigned(i, length));
    end;

begin

    tmp_sum <= o_tmp + stepint;

    process(clk)
      begin
        if rising_edge(clk) then
            if rst_n = '0' then
                o_tmp   <= i2sv(0);
                stepint <= i2sv(1);

            elsif step = '1' then
                o_tmp <= tmp_sum;

                if (double = 1) and (tmp_sum = i2sv(0) or tmp_sum = i2sv(maxval)) then
                    stepint <= (not stepint) + 1;
                end if;
            end if;
        end if;
    end process;

    ramp <= o_tmp;

end;
