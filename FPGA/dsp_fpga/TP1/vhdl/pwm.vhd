library IEEE;
use IEEE.std_logic_1164.all;
use ieee.math_real.all;
use IEEE.numeric_std.all;
use ieee.std_logic_unsigned.all;

entity PWM is
    generic (
        duty_bits : integer := 1;
        freq      : integer := 10000;
        sys_freq  : integer := 100000000
    );
    port(
        rst_n :  in std_logic;
        clk   :  in std_logic;
        duty  :  in std_logic_vector(duty_bits - 1 downto 0);
        en    :  in std_logic;
        pwm   : out std_logic := '0'
    );
end;

architecture rtl of PWM is
    constant lim      : integer := sys_freq / freq;
    constant lim_bits : integer := integer(ceil(log2(real(lim + 1))));

    signal o_tmp      : std_logic := '0';
    signal rst_tmp    : std_logic;

    signal counter    : std_logic_vector(lim_bits - 1 downto 0) := (others => '0');
    signal mul        : std_logic_vector(DUTY_BITS + lim_bits - 1 downto 0) := (others => '0');

    function i2sv(
        i      : in integer;
        length : in integer := counter'length
    ) return std_logic_vector is
        begin
            return std_logic_vector(to_unsigned(i, length));
    end;

begin

    rst_tmp <= std_logic((not rst_n) and (not en));
    mul     <= duty * i2sv(lim, lim_bits);

    process(clk)
      begin
        if rising_edge(clk) then
            if rst_tmp = '0' then
                if counter = i2sv(lim - 1) then
                    counter <= i2sv(0);
                else
                    counter <= counter + i2sv(1);
                end if;

                if counter < mul(DUTY_BITS + lim_bits - 1 downto DUTY_BITS) then
                    o_tmp <= '1';
                else
                    o_tmp <= '0';
                end if;
            else
                counter <= i2sv(0);
                o_tmp   <= '0';
            end if;
        end if;
    end process;

    pwm <= o_tmp;

end;