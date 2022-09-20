library IEEE;
use IEEE.std_logic_1164.all;
use ieee.math_real.all;
use IEEE.numeric_std.all;
use ieee.std_logic_unsigned.all;

entity PWMOnePhase is
    generic (
        duty_bits : integer := 1;
        freq      : integer := 10000;
        sys_freq  : integer := 100000000
    );
    port(
        rst_n :  in std_logic;
        clk   :  in std_logic;
        duty  :  in integer range 0 to 2**duty_bits - 1;
        en    :  in std_logic;
        pwm   : out std_logic := '0'
    );
end;

architecture rtl of PWMOnePhase is
    constant lim      : integer := sys_freq / freq;

    signal o_tmp      : std_logic := '0';
    signal rst_tmp    : std_logic;
    signal counter    : integer range 0 to lim - 1 := 0;
    signal mul        : integer range 0 to lim * (2**duty_bits - 1) := 0;

begin

    rst_tmp <= std_logic((not rst_n) and (not en));
    mul     <= duty * lim;

    process(clk)
      begin
        if rising_edge(clk) then
            if (rst_n = '1') then
                if counter = lim - 1 then
                    counter <= 0;
                else
                    counter <= counter + 1;
                end if;

                if counter < (mul / 2**duty_bits) then
                    o_tmp <= '1';
                else
                    o_tmp <= '0';
                end if;
            else
                counter <=  0 ;
                o_tmp   <= '0';
            end if;
        end if;
    end process;

    pwm <= o_tmp;

end;


library IEEE;
use IEEE.std_logic_1164.all;
use ieee.math_real.all;
use IEEE.numeric_std.all;
use ieee.std_logic_unsigned.all;

entity PWM is
    generic (
        duty_bits : integer := 1;
        freq      : integer := 10000;
        sys_freq  : integer := 100000000;
        phases    : integer range 1 to 8 := 1
    );
    port(
        rst_n :  in std_logic;
        clk   :  in std_logic;
        duty  :  in integer range 0 to 2**duty_bits - 1;
        en    :  in std_logic;
        pwm   : out std_logic_vector(phases - 1 downto 0) := (others => '0');
        pwm_n : out std_logic_vector(phases - 1 downto 0) := (others => '1')
    );
end;

architecture rtl of PWM is
    signal o_tmp : std_logic_vector(phases - 1 downto 0) := (others => '0');

    type count_type is array(0 to phases-1) of integer range 0 to sys_freq / freq;
    type ens_type   is array(0 to phases-1) of std_logic;

    signal counters : count_type := (others =>  0 );
    signal ens      : ens_type   := (others => '0');

    component PWMOnePhase
        generic (
            duty_bits : integer := 1;
            freq      : integer := 10000;
            sys_freq  : integer := 100000000
        );
        port(
            rst_n :  in std_logic;
            clk   :  in std_logic;
            duty  :  in integer range 0 to 2**duty_bits - 1;
            en    :  in std_logic;
            pwm   : out std_logic := '0'
        );
    end component;

begin

    p0: for i in 0 to phases - 1 generate
        begin
            pwm0: PWMOnePhase
                generic map(
                    duty_bits => duty_bits,
                    freq => freq,
                    sys_freq => sys_freq
                )
                port map(
                    rst_n => rst_n,
                    clk => clk,
                    duty => duty,
                    en => ens(i),
                    pwm => o_tmp(i)
                );

            ens(i) <= en when counters(i) >= (i * sys_freq / freq) else '0';
            process(clk)
                begin
                    if rising_edge(clk) then
                        if (rst_n = '1') and (en = '1') then
                            if ens(i) = '0' then
                                counters(i) <= counters(i) + 1;
                            end if;
                        else
                            counters(i) <= 0;
                        end if;
                    end if;
            end process;
    end generate;

    pwm   <= o_tmp;
    pwm_n <= not o_tmp;
end;