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
    signal counter       : integer range 0 to div_half - 1 :=  0 ;
    signal tmp_o, tmp_re : std_logic                       := '0';

begin

    process(clk)
      begin
        if rising_edge(clk) then
            if rst_n = '1' then
                if counter < div_half - 1 then
                    counter <= counter + 1;
                    tmp_re  <= '0';
                else
                    counter <= 0;
                    tmp_o   <= not tmp_o;
                    tmp_re  <= '1';
                end if;
            else
                counter <=  0 ;
                tmp_o   <= '0';
                tmp_re  <= '0';
            end if;
        end if;
    end process;

    freqdiv <= tmp_o;
    re      <= tmp_re;

end;