// Flow-validation sequencer and classifier (behaviour: SPEC.md v0.2).
//
// Why timestamp-driven: every decision is a function of the per-electrode capture timestamps
// (capture_unit) and of the window predicate  (x - t_prev) * A > B,  never of when in clock time a
// comparison happens. An arrival at tick m is acted on only once it is final: no electrode is still
// in its glitch filter, and now > m, so no other electrode can still be stamped m. A timeout seen
// at a sampled tick x is final because any later capture has ts >= x and the predicate is
// monotonic in x. Hence the result is independent of the clock-to-tick ratio and of the latency of
// the time-shared multiplier, which is what lets the regression run one tick per clock.
//
// The scan works on a snapshot (S_SCAN) of all captures and `now` taken in one clock, and walks it
// over several clocks (min, ties, finality); a capture after the snapshot has ts >= snapshot now,
// so it cannot change a decision the snapshot calls final.
//
// Arithmetic: one multiplier, (measured time) x (constant from params_pkg); 64-bit comparisons,
// no divider. Requires N >= 2.
module detector_core import params_pkg::*; #(
  parameter int DEB = 4
) (
  input  logic         clk,
  input  logic         rst_n,
  input  logic         tick,      // 1 ms timebase strobe
  input  logic         arm,       // sample applied: t = 0
  input  logic [N-1:0] arr_s,     // synchronized electrode lines
  output logic         valid,     // one-cycle pulse with the result
  output cls_t         cls,
  output logic [2:0]   loc
);
  typedef logic [TS_BITS-1:0] ts_t;
  typedef logic [63:0]        w_t;
  typedef enum logic [3:0] {S_IDLE, S_STAGE, S_BSET, S_SCAN, S_MIN, S_TIE, S_ISSUE, S_TESTM, S_TESTN,
                            S_CLS0, S_CLS1, S_CLS2, S_CLS3, S_UNI, S_REPORT, S_MUL} state_t;

  state_t     state, ret;
  logic [2:0] idx, k;                 // stage (electrode awaited); classifier segment
  ts_t        now, t_prev, m_snap;
  ts_t        dt [N];                 // captured segment times
  logic [N-1:0] amask;                // electrodes stamped with the earliest tick m_snap
  w_t         B, lhs;
  logic       wcnt;

  // ---- timestamp unit: one capture per electrode ----
  logic         clr, run;
  logic [N-1:0] pend, capd;
  ts_t          ts [N];
  assign clr = (state == S_IDLE) && arm;
  assign run = (state != S_IDLE) && (state != S_REPORT);
  for (genvar j = 0; j < N; j++) begin : g_cap
    capture_unit #(.TSW(TS_BITS), .DEB(DEB)) u_cap (
      .clk, .rst_n, .clr, .en(run), .d(arr_s[j]), .now,
      .pending(pend[j]), .captured(capd[j]), .ts(ts[j]));
  end

  // ---- shared multiplier ----
  ts_t                     ma;
  logic [MBW-1:0]          mb;
  logic [TS_BITS+MBW-1:0]  p;
  w_t                      pw;
  mul_u #(.AW(TS_BITS), .BW(MBW)) u_mul (.clk, .a(ma), .b(mb), .p);
  assign pw = w_t'(p);

  // ---- scan of the electrodes still awaited (j >= idx), on a registered snapshot ----
  logic [N-1:0] cand, others, s_cand;
  logic         anyp, s_pend, have, fin;
  ts_t          s_ts [N];
  ts_t          s_now;
  logic [2:0]   jj;
  always_comb begin
    anyp = 1'b0;
    for (int j = 0; j < N; j++) begin
      cand[j]   = capd[j] && (j >= idx);
      anyp     |= pend[j] && (j >= idx);
      others[j] = amask[j] && (j != idx);
    end
  end

  function automatic logic [2:0] lowest(input logic [N-1:0] v);
    lowest = '0;
    for (int j = N-1; j >= 0; j--) if (v[j]) lowest = 3'(j);
  endfunction

  // window multiplier operand: A = 256 at stage 0, E0*256 later (the <<8 is applied to the product)
  logic [MBW-1:0] a_win;
  assign a_win = (idx == 0) ? MBW'(1) : MBW'(E[0]);

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      state <= S_IDLE; ret <= S_IDLE; idx <= '0; k <= '0; now <= '0; t_prev <= '0; m_snap <= '0;
      amask <= '0; B <= '0; lhs <= '0; wcnt <= 1'b0; ma <= '0; mb <= '0;
      valid <= 1'b0; cls <= NOMINAL; loc <= '0;
      s_cand <= '0; s_pend <= 1'b0; s_now <= '0; have <= 1'b0; fin <= 1'b0; jj <= '0;
      for (int j = 0; j < N; j++) begin dt[j] <= '0; s_ts[j] <= '0; end
    end else begin
      valid <= 1'b0;
      if (clr)                             now <= '0;
      else if (run && tick && now != '1)   now <= now + 1'b1;     // saturating timebase

      unique case (state)
        S_IDLE: if (arm) begin
          t_prev <= '0; idx <= '0;
          if (|arr_s) begin cls <= SENSOR; loc <= lowest(arr_s); state <= S_REPORT; end  // high before arm
          else state <= S_STAGE;
        end

        // stage window bound B: stage 0 a constant, later dt0 * E_idx * (256 + TOL_STALL)
        S_STAGE: if (idx == 0) begin B <= B_FIRST; state <= S_SCAN; end
                 else begin ma <= dt[0]; mb <= MBW'(C_STALL[idx]); ret <= S_BSET; wcnt <= 1'b1; state <= S_MUL; end
        S_BSET:  begin B <= pw; state <= S_SCAN; end

        S_SCAN: begin                                           // snapshot
          for (int j = 0; j < N; j++) s_ts[j] <= ts[j];
          s_cand <= cand; s_pend <= anyp; s_now <= now;
          m_snap <= '1; have <= 1'b0; jj <= '0; state <= S_MIN;
        end
        S_MIN: begin                                            // earliest stamp, one electrode per clock
          if (s_cand[jj] && s_ts[jj] < m_snap) m_snap <= s_ts[jj];
          have <= have | s_cand[jj];
          if (jj == N-1) state <= S_TIE; else jj <= jj + 1'b1;
        end
        S_TIE: begin
          for (int j = 0; j < N; j++) amask[j] <= s_cand[j] && (s_ts[j] == m_snap);
          fin <= have && (s_now > m_snap);                      // no electrode can still be stamped m
          state <= S_ISSUE;
        end
        S_ISSUE:
          if (s_pend) state <= S_SCAN;                          // a glitch filter is still deciding
          else begin
            ret <= fin ? S_TESTM : S_TESTN;
            ma  <= (fin ? m_snap : s_now) - t_prev;             // earliest arrival, or expiry check
            mb  <= a_win; wcnt <= 1'b1; state <= S_MUL;
          end

        S_TESTM:
          if ((pw << 8) > B) begin cls <= STALL; loc <= idx; state <= S_REPORT; end          // arrived too late
          else if (|others) begin                                                           // out-of-order / tie
            cls <= SENSOR; loc <= amask[idx] ? lowest(others) : idx; state <= S_REPORT;
          end else begin
            dt[idx] <= m_snap - t_prev; t_prev <= m_snap;
            if (idx == 0 && (w_t'(m_snap) << 8) < MIN_FIRST) begin                           // implausibly fast
              cls <= SENSOR; loc <= '0; state <= S_REPORT;
            end else if (idx == N-1) begin k <= 3'd1; state <= S_CLS0; end
            else begin idx <= idx + 1'b1; state <= S_STAGE; end
          end

        S_TESTN: if ((pw << 8) > B) begin cls <= STALL; loc <= idx; state <= S_REPORT; end
                 else state <= S_SCAN;

        // classifier: first k with dt_k*E0*256 outside dt0*E_k*(256 +/- TOL)
        S_CLS0: begin ma <= dt[k]; mb <= MBW'(E[0]); ret <= S_CLS1; wcnt <= 1'b1; state <= S_MUL; end
        S_CLS1: begin lhs <= pw << 8; ma <= dt[0]; mb <= MBW'(C_HI[k]); ret <= S_CLS2; wcnt <= 1'b1; state <= S_MUL; end
        S_CLS2: if (lhs > pw) begin cls <= RESTRICTION; loc <= k; state <= S_REPORT; end
                else begin ma <= dt[0]; mb <= MBW'(C_LO[k]); ret <= S_CLS3; wcnt <= 1'b1; state <= S_MUL; end
        S_CLS3: if (lhs < pw) begin cls <= ANOMALY; loc <= k; state <= S_REPORT; end
                else if (k == N-1) state <= S_UNI;
                else begin k <= k + 1'b1; state <= S_CLS0; end

        // all segments consistent with one K: test the total fill time against the nominal band
        S_UNI: begin
          loc <= '0; state <= S_REPORT;
          if      ((w_t'(t_prev) << 8) > U_HI) cls <= UNIFORM_SLOW;
          else if ((w_t'(t_prev) << 8) < U_LO) cls <= UNIFORM_FAST;
          else                                  cls <= NOMINAL;
        end

        S_REPORT: begin valid <= 1'b1; state <= S_IDLE; end

        // wait for the 2-stage multiplier, then resume at `ret`
        S_MUL: if (wcnt) wcnt <= 1'b0; else state <= ret;

        default: state <= S_IDLE;
      endcase
    end
  end

`ifndef SYNTHESIS
  `include "detector_core_checks.svh"   // SVA + functional coverage (tb/)
`endif
endmodule
