// Shared unsigned multiplier, measured time x constant. Two register stages (M, P) so Vivado maps
// it onto cascaded DSP48E1 slices; the operand registers live in the sequencer.
// Result valid 2 clocks after the operands change.
module mul_u #(
  parameter int AW = 24,
  parameter int BW = 36
) (
  input  logic             clk,
  input  logic [AW-1:0]    a,
  input  logic [BW-1:0]    b,
  output logic [AW+BW-1:0] p
);
  (* use_dsp = "yes" *) logic [AW+BW-1:0] m;
  always_ff @(posedge clk) begin
    m <= a * b;
    p <= m;
  end
endmodule
