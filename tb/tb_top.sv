// File-driven corpus testbench. Reads stim.txt and writes rtl_out.txt (id cls loc) in the working
// directory. Stimulus line:  id t_0..t_{N-1} ng [j g w]*ng
//   t_k: arrival tick (-1 never, -2 high before arm); then ng glitches, each a w-clock pulse on
//   electrode j starting at tick g (the glitch filter accepts it as an arrival iff w >= DEB).
//
// Timebase: the TB drives `tick` and mirrors the DUT's tick count k (no hierarchical references).
// It ticks on EVERY clock, except that after raising an electrode line at tick k it holds `tick`
// low for 3 clocks, the synchronizer-plus-capture latency, so the line is stamped exactly k.
// Running the timebase 10^5x faster than in silicon makes ~2e9 corpus ticks simulable and checks
// that decisions do not depend on the clock-to-tick ratio.
`timescale 1ns/1ps
module tb_top;
  import params_pkg::*;
  localparam int DEB = 4;

  logic clk = 0, rst_n = 0, arm = 0, tick = 0;
  logic [N-1:0] arrive = '0;
  logic valid; cls_t cls; logic [2:0] loc;
  always #5 clk = ~clk;

  detector_top #(.DEB(DEB)) dut (.clk, .rst_n, .tick, .arm, .arrive_async(arrive), .valid, .cls, .loc);

  int t [N], gt [N], gw [N], gl [N];
  int fin, fout, id, r, n_run = 0, hold, ng, gj, gg, gww;
  longint k;
  bit got;

  initial begin
    fin = $fopen("stim.txt", "r"); fout = $fopen("rtl_out.txt", "w");
    if (fin == 0) $fatal(1, "cannot open stim.txt");
    repeat (4) @(negedge clk); rst_n = 1;
    forever begin
      r = $fscanf(fin, "%d", id);
      if (r != 1) break;
      for (int j = 0; j < N; j++) r = $fscanf(fin, "%d", t[j]);
      for (int j = 0; j < N; j++) begin gt[j] = -1; gw[j] = 0; gl[j] = 0; end
      r = $fscanf(fin, "%d", ng);
      for (int i = 0; i < ng; i++) begin                // at most one glitch per electrode
        r = $fscanf(fin, "%d %d %d", gj, gg, gww);
        gt[gj] = gg; gw[gj] = gww;
      end

      arrive = '0; tick = 0;
      for (int j = 0; j < N; j++) if (t[j] == -2) arrive[j] = 1'b1;
      repeat (4) @(negedge clk);                       // let pre-high lines through the synchronizer
      arm = 1; @(negedge clk); arm = 0; tick = 1;      // posedge sampled arm: now <= 0
      k = 0; hold = 0; got = 0;
      while (!got) begin
        @(negedge clk);
        if (valid) begin
          $fdisplay(fout, "%0d %0d %0d", id, cls, loc);
          got = 1;
        end else begin
          if (tick) k++;                               // the posedge just passed advanced now to k
          if (k > 64'd16_000_000) $fatal(1, "watchdog: scenario %0d never reported", id);
          tick = 1;
          if (hold > 0) begin hold--; tick = 0; end
          for (int j = 0; j < N; j++)                     // end of a glitch pulse
            if (gl[j] > 0) begin gl[j]--; if (gl[j] == 0) arrive[j] = 1'b0; end
          for (int j = 0; j < N; j++) begin
            if (t[j] == k && !arrive[j]) begin arrive[j] = 1'b1; tick = 0; hold = 2; end
            if (gt[j] == k && gl[j] == 0 && !arrive[j]) begin
              arrive[j] = 1'b1; gl[j] = gw[j]; gt[j] = -1; tick = 0; hold = 2;
            end
          end
        end
      end
      tick = 0; arrive = '0;
      n_run++;
      repeat (4) @(negedge clk);
    end
    $fclose(fout);
    $display("TB_DONE scenarios=%0d", n_run);
    $finish;
  end
endmodule
