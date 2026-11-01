// White-box assertions and functional coverage for detector_core (included in its scope,
// simulation only). Window predicates are recomputed from the RAW tolerances in params_pkg,
// not from the folded ROM constants the RTL uses.

// ======================================================================== assertions
function automatic bit legal_step(state_t a, state_t b);
  case (a)
    S_IDLE:   return b inside {S_IDLE, S_STAGE, S_REPORT};
    S_STAGE:  return b inside {S_SCAN, S_MUL};
    S_BSET:   return b == S_SCAN;
    S_SCAN:   return b == S_MIN;
    S_MIN:    return b inside {S_MIN, S_TIE};
    S_TIE:    return b == S_ISSUE;
    S_ISSUE:  return b inside {S_SCAN, S_MUL};
    S_TESTM:  return b inside {S_REPORT, S_CLS0, S_STAGE};
    S_TESTN:  return b inside {S_REPORT, S_SCAN};
    S_CLS0:   return b == S_MUL;
    S_CLS1:   return b == S_MUL;
    S_CLS2:   return b inside {S_REPORT, S_MUL};
    S_CLS3:   return b inside {S_REPORT, S_UNI, S_CLS0};
    S_UNI:    return b == S_REPORT;
    S_REPORT: return b == S_IDLE;
    S_MUL:    return b inside {S_MUL, S_BSET, S_TESTM, S_TESTN, S_CLS1, S_CLS2, S_CLS3};
    default:  return 1'b0;
  endcase
endfunction

// window predicate of SPEC.md, stage L, elapsed e since the previous arrival
function automatic bit expired(longint unsigned e, int L, longint unsigned dt0v);
  if (L == 0) return e * 256 > E[0] * FIRST_Q;
  return e * E[0] * 256 > dt0v * E[L] * (256 + TOL_STALL_Q);
endfunction

state_t prev_state = S_IDLE;                      // state in the previous clock
always @(posedge clk) prev_state <= rst_n ? state : S_IDLE;

// FSM structure
a_legal:     assert property (@(posedge clk) disable iff (!rst_n) legal_step(prev_state, state))
             else $error("illegal transition %s -> %s", prev_state.name(), state.name());
a_mul_ret:   assert property (@(posedge clk) disable iff (!rst_n) (state == S_MUL && !wcnt) |=> state == $past(ret));
a_mul_hold:  assert property (@(posedge clk) disable iff (!rst_n)
                              (state == S_MUL && $past(state) == S_MUL) |-> ($stable(ma) && $stable(mb)));
a_idx_step:  assert property (@(posedge clk) disable iff (!rst_n)
                              ($past(state) != S_IDLE) |-> (idx == $past(idx) || idx == $past(idx) + 1));
a_idx_range: assert property (@(posedge clk) disable iff (!rst_n) idx < N && k < N);

// exactly one result per run
int unsigned n_arm = 0, n_valid = 0;
always @(posedge clk) if (rst_n) begin
  if (state == S_IDLE && arm) n_arm++;
  if (valid) n_valid++;
end
a_valid_src:  assert property (@(posedge clk) disable iff (!rst_n) valid |-> $past(state) == S_REPORT);
a_valid_one:  assert property (@(posedge clk) disable iff (!rst_n) valid |=> !valid);
a_valid_run:  assert property (@(posedge clk) disable iff (!rst_n) valid |-> n_valid + 1 == n_arm);
a_arm_clean:  assert property (@(posedge clk) disable iff (!rst_n) (state == S_IDLE && arm) |-> n_valid == n_arm);
final if (n_valid != n_arm) $error("runs started %0d, results %0d", n_arm, n_valid);

// timebase and timestamps are monotonic within a run
a_now_step:  assert property (@(posedge clk) disable iff (!rst_n)
                              (run && $past(run)) |-> (now == $past(now) || now == $past(now) + 1));
a_now_nosat: assert property (@(posedge clk) disable iff (!rst_n) run |-> now != '1)
             else $error("timebase saturated during a run");
a_tprev_mono: assert property (@(posedge clk) disable iff (!rst_n)
                               ($past(state) != S_IDLE && state != S_IDLE) |-> t_prev >= $past(t_prev));
for (genvar j = 0; j < N; j++) begin : g_cap_chk
  // glitch filter: a capture needs the synchronized line high on the DEB preceding clocks
  logic [DEB-1:0] hist = '0;
  always @(posedge clk) hist <= rst_n ? ((hist << 1) | DEB'(arr_s[j])) : '0;
  a_filter:  assert property (@(posedge clk) disable iff (!rst_n) $rose(capd[j]) |-> &hist)
             else $error("electrode %0d captured after a pulse shorter than %0d clocks", j, DEB);
  a_ts_hold: assert property (@(posedge clk) disable iff (!rst_n) (capd[j] && $past(capd[j])) |-> $stable(ts[j]));
  a_ts_past: assert property (@(posedge clk) disable iff (!rst_n) capd[j] |-> ts[j] <= now);
  a_pend_x:  assert property (@(posedge clk) disable iff (!rst_n) !(pend[j] && capd[j]));
end

// no result before the evidence for it exists, and none built on evidence that should have been
// rejected: every ACCEPTED stage (all N for a classification, the first `idx` for STALL/SENSOR)
// arrived in order, inside its window, with a plausible first segment
always @(posedge clk) if (rst_n && valid) begin
  automatic longint unsigned tp, dt0v;
  automatic int acc;
  automatic bit classified = cls inside {NOMINAL, UNIFORM_SLOW, UNIFORM_FAST, RESTRICTION, ANOMALY};
  acc = classified ? N : int'(idx);
  for (int j = 0; j < N; j++) if (j < acc) begin
    tp = (j == 0) ? 0 : ts[j-1];
    a_arrived: assert (capd[j]) else $error("%s: stage %0d used without an arrival", cls.name(), j);
    a_order:   assert (j == 0 || ts[j] > ts[j-1]) else $error("%s: arrivals out of order at %0d", cls.name(), j);
    a_dt:      assert (dt[j] == ts[j] - tp) else $error("%s: dt[%0d] != ts difference", cls.name(), j);
    a_inwin:   assert (!expired(ts[j] - tp, j, ts[0]))
               else $error("%s: arrival %0d accepted outside its window", cls.name(), j);
  end
  if (acc > 0) a_minfirst: assert (longint'(ts[0]) * 256 >= E[0] * MIN_FIRST_Q)
               else $error("%s: implausible first segment accepted", cls.name());
  if (classified)
    a_loc_cls: assert ((cls inside {RESTRICTION, ANOMALY}) ? (loc >= 1 && loc < N) : (loc == 0));
  if (cls == STALL) begin
    // stalled at stage loc: every later electrode absent or outside the window, and the window
    // had actually expired when the result was given
    tp   = (loc == 0) ? 0 : ts[loc-1];
    dt0v = ts[0];
    a_stall_idx: assert (idx == loc);
    for (int j = 0; j < N; j++) if (j >= loc)
      a_stall_late: assert (!capd[j] || expired(ts[j] - tp, loc, dt0v))
                    else $error("STALL at %0d but electrode %0d arrived in window", loc, j);
    a_stall_expired: assert (expired(now - tp, loc, dt0v)) else $error("STALL before window expiry");
  end
  a_loc_range: assert (loc < N);
end

// ======================================================================== coverage
logic [7:0] trans;
assign trans = {4'(prev_state), 4'(state)};
`define T(a, b) {4'(a), 4'(b)}

covergroup cg_fsm @(posedge clk iff (rst_n && prev_state != state));
  option.per_instance = 1;
  cp_trans: coverpoint trans {
    bins idle_stage   = {`T(S_IDLE, S_STAGE)};    bins idle_report = {`T(S_IDLE, S_REPORT)};
    bins stage_scan   = {`T(S_STAGE, S_SCAN)};    bins stage_mul   = {`T(S_STAGE, S_MUL)};
    bins bset_scan    = {`T(S_BSET, S_SCAN)};     bins scan_min    = {`T(S_SCAN, S_MIN)};
    bins min_tie      = {`T(S_MIN, S_TIE)};       bins tie_issue   = {`T(S_TIE, S_ISSUE)};
    bins issue_scan   = {`T(S_ISSUE, S_SCAN)};    bins issue_mul   = {`T(S_ISSUE, S_MUL)};
    bins testm_report = {`T(S_TESTM, S_REPORT)};  bins testm_cls0  = {`T(S_TESTM, S_CLS0)};
    bins testm_stage  = {`T(S_TESTM, S_STAGE)};   bins testn_report = {`T(S_TESTN, S_REPORT)};
    bins testn_scan   = {`T(S_TESTN, S_SCAN)};    bins cls0_mul    = {`T(S_CLS0, S_MUL)};
    bins cls1_mul     = {`T(S_CLS1, S_MUL)};      bins cls2_report = {`T(S_CLS2, S_REPORT)};
    bins cls2_mul     = {`T(S_CLS2, S_MUL)};      bins cls3_report = {`T(S_CLS3, S_REPORT)};
    bins cls3_uni     = {`T(S_CLS3, S_UNI)};      bins cls3_cls0   = {`T(S_CLS3, S_CLS0)};
    bins uni_report   = {`T(S_UNI, S_REPORT)};    bins report_idle = {`T(S_REPORT, S_IDLE)};
    bins mul_bset     = {`T(S_MUL, S_BSET)};      bins mul_testm   = {`T(S_MUL, S_TESTM)};
    bins mul_testn    = {`T(S_MUL, S_TESTN)};     bins mul_cls1    = {`T(S_MUL, S_CLS1)};
    bins mul_cls2     = {`T(S_MUL, S_CLS2)};      bins mul_cls3    = {`T(S_MUL, S_CLS3)};
  }
endgroup

covergroup cg_state @(posedge clk iff (rst_n && prev_state != state));   // every state is entered
  option.per_instance = 1;
  cp_state: coverpoint state;
endgroup

// every result class at every physically meaningful location; code = class*8 + loc.
// Plain integer bounds: xsim 2022.2 mis-evaluates sized casts inside bin ranges.
localparam int RC_NOM = 8 * int'(NOMINAL),  RC_US = 8 * int'(UNIFORM_SLOW), RC_UF = 8 * int'(UNIFORM_FAST);
localparam int RC_R   = 8 * int'(RESTRICTION), RC_A = 8 * int'(ANOMALY);
localparam int RC_ST  = 8 * int'(STALL),       RC_SE = 8 * int'(SENSOR);
int res_code;
assign res_code = 8 * int'(cls) + int'(loc);

covergroup cg_result @(posedge clk iff (rst_n && valid));
  option.per_instance = 1;
  cp_res: coverpoint res_code {
    bins nominal  = {RC_NOM};
    bins u_slow   = {RC_US};
    bins u_fast   = {RC_UF};
    bins restr[]  = {[RC_R + 1 : RC_R + N - 1]};
    bins anom[]   = {[RC_A + 1 : RC_A + N - 1]};
    bins stall[]  = {[RC_ST : RC_ST + N - 1]};
    bins sensor[] = {[RC_SE : RC_SE + N - 1]};
  }
endgroup

// boundary behaviour
logic glitch_rej, tie_with, tie_without, fast_first, win_edge, hi_edge, lo_edge, pre_high;
always_comb begin
  glitch_rej = 1'b0;
  for (int j = 0; j < N; j++) glitch_rej |= run && pend[j] && !arr_s[j];         // filter rejects a pulse
  tie_with    = (state == S_TESTM) && ((pw << 8) <= B) && |others && amask[idx];
  tie_without = (state == S_TESTM) && ((pw << 8) <= B) && |others && !amask[idx];
  fast_first  = (state == S_TESTM) && ((pw << 8) <= B) && !(|others) && idx == 0
                && (w_t'(m_snap) << 8) < MIN_FIRST;
  win_edge    = (state inside {S_TESTM, S_TESTN}) && ((pw << 8) == B);           // exactly on the window edge
  hi_edge     = (state == S_CLS2) && (lhs == pw);
  lo_edge     = (state == S_CLS3) && (lhs == pw);
  pre_high    = (state == S_IDLE) && arm && |arr_s;
end

// the TEST/CLS states last one clock and are always entered by a change, so sampling on
// state changes, arm and filter rejections sees every boundary event
covergroup cg_boundary @(posedge clk iff (rst_n && (prev_state != state || arm || glitch_rej)));
  option.per_instance = 1;
  cp_glitch_rejected: coverpoint glitch_rej { bins hit = {1}; }
  cp_tie_incl_idx:    coverpoint tie_with    { bins hit = {1}; }
  cp_tie_excl_idx:    coverpoint tie_without { bins hit = {1}; }
  cp_fast_first:      coverpoint fast_first  { bins hit = {1}; }
  cp_window_edge:     coverpoint win_edge    { bins hit = {1}; }
  cp_tol_hi_edge:     coverpoint hi_edge     { bins hit = {1}; }
  cp_tol_lo_edge:     coverpoint lo_edge     { bins hit = {1}; }
  cp_pre_high:        coverpoint pre_high    { bins hit = {1}; }
  cp_stall_idx:       coverpoint idx iff (state == S_TESTN && (pw << 8) > B) { bins s[] = {[0:N-1]}; }
endgroup

cg_fsm      u_cg_fsm      = new();
cg_state    u_cg_state    = new();
cg_result   u_cg_result   = new();
cg_boundary u_cg_boundary = new();
`undef T
