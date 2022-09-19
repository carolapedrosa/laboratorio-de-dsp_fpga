library IEEE;
use IEEE.std_logic_1164.all;
use ieee.math_real.all;
use IEEE.numeric_std.all;
use ieee.std_logic_unsigned.all;

entity Freqdiv is
    generic (
        div_half : integer := 1
    );
    port(
        rst_n   :  in std_logic;
        clk     :  in std_logic;
        freqdiv : out std_logic := '0';
        re      : out std_logic := '0'
    );
end;

architecture rtl of Freqdiv is
    signal counter : std_logic_vector(integer(ceil(log2(real(div_half)))) - 1 downto 0) := (others => '0');

    signal tmp_o, tmp_re : std_logic := '0';

    function i2sv(
        i      : in integer;
        length : in integer := counter'length
    ) return std_logic_vector is
        begin
            return std_logic_vector(to_unsigned(i, length));
    end;

begin

    process(clk)
      begin
        if rising_edge(clk) then
            if (rst_n = '1') and (counter < i2sv(div_half - 1)) then
                counter <= counter + i2sv(1);
            else
                counter <= i2sv(0);
            end if;

            if (rst_n = '1') and (counter = i2sv(0)) then
                tmp_o   <= not tmp_o;
                tmp_re  <= '1';
            else
                tmp_o   <= '0';
                tmp_re  <= '0';
            end if;

        end if;
    end process;

    freqdiv <= tmp_o;
    re      <= tmp_re;

end;