// Per-electrode input capture (timestamp unit).
// Glitch filter: the synchronized line must stay high for DEB consecutive clocks. The timestamp is
// the tick count at the START of that high run, so the filter adds latency but no timestamp error.
// Only the first accepted rise per run is kept (the wetting front passes an electrode once).
module capture_unit #(
  parameter int TSW = 24,
  parameter int DEB = 4
) (
  input  logic           clk,
  input  logic           rst_n,
  input  logic           clr,       // start of a run: forget previous capture
  input  logic           en,        // run in progress
  input  logic           d,         // synchronized comparator output
  input  logic [TSW-1:0] now,
  output logic           pending,   // high run in progress, not yet accepted
  output logic           captured,
  output logic [TSW-1:0] ts
);
  logic [$clog2(DEB+1)-1:0] cnt;

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      pending <= 1'b0; captured <= 1'b0; ts <= '0; cnt <= '0;
    end else if (clr) begin
      pending <= 1'b0; captured <= 1'b0; cnt <= '0;
    end else if (en && !captured) begin
      if (!d) begin                       // idle, or a glitch shorter than DEB: reject
        pending <= 1'b0; cnt <= '0;
      end else if (!pending) begin        // first high clock: provisional timestamp
        ts <= now;
        if (DEB <= 1) captured <= 1'b1;
        else begin pending <= 1'b1; cnt <= 1; end
      end else if (cnt == DEB-1) begin
        pending <= 1'b0; captured <= 1'b1;
      end else begin
        cnt <= cnt + 1'b1;
      end
    end
  end
endmodule
