// Multi-electrode capillary-flow fault detector (interface A: one digital arrival line per electrode).
// The 1 ms `tick` strobe comes from a shared timebase (tick_gen in the synthesis wrapper).
module detector_top import params_pkg::*; #(
  parameter int DEB = 4                     // glitch filter, clocks
) (
  input  logic         clk,
  input  logic         rst_n,
  input  logic         tick,
  input  logic         arm,
  input  logic [N-1:0] arrive_async,        // comparator outputs, high once wetted
  output logic         valid,
  output cls_t         cls,
  output logic [2:0]   loc
);
  logic [N-1:0] arr_s;
  sync2 #(.W(N)) u_sync (.clk, .rst_n, .d(arrive_async), .q(arr_s));
  detector_core #(.DEB(DEB)) u_core (.clk, .rst_n, .tick, .arm, .arr_s, .valid, .cls, .loc);
endmodule
