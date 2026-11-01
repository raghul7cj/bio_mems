# 100 MHz system clock (PYNQ-Z2 PL fabric clock from the PS, FCLK_CLK0).
create_clock -period 10.000 -name clk [get_ports clk]
