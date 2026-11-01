// Two-flop synchronizer for asynchronous electrode comparator outputs.
module sync2 #(parameter int W = 1) (
  input  logic         clk,
  input  logic         rst_n,
  input  logic [W-1:0] d,
  output logic [W-1:0] q
);
  logic [W-1:0] m;
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) begin m <= '0; q <= '0; end
    else        begin m <= d;  q <= m;  end
endmodule
