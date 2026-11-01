// Synthesis wrapper: 100 MHz clock, 1 ms tick generator, 10 us glitch filter.
module tick_gen #(parameter int DIV = 100_000) (
  input  logic clk,
  input  logic rst_n,
  output logic tick
);
  logic [$clog2(DIV)-1:0] c;
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) begin c <= '0; tick <= 1'b0; end
    else begin
      tick <= (c == DIV-1);
      c    <= (c == DIV-1) ? '0 : c + 1'b1;
    end
endmodule

module detector_syn_top import params_pkg::*; #(
  parameter int TICK_DIV = 100_000,
  parameter int DEB      = 1000
) (
  input  logic         clk,
  input  logic         rst_n,
  input  logic         arm,
  input  logic [N-1:0] arrive_async,
  output logic         valid,
  output logic [2:0]   cls_o,
  output logic [2:0]   loc
);
  logic tick;
  cls_t cls;
  tick_gen #(.DIV(TICK_DIV)) u_tick (.clk, .rst_n, .tick);
  detector_top #(.DEB(DEB)) u_det (.clk, .rst_n, .tick, .arm, .arrive_async, .valid, .cls, .loc);
  assign cls_o = cls;
endmodule
