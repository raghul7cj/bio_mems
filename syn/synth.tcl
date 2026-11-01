# Vivado batch flow (out-of-context): synth + place + route for the PYNQ-Z2 part, then reports.
# Run from build/syn:  vivado -mode batch -source ../../syn/synth.tcl
set root  [file normalize [file join [pwd] .. ..]]
set build [pwd]
set part  xc7z020clg400-1

read_verilog -sv [list \
  [file join $build params_pkg.sv] \
  [file join $root rtl sync2.sv] \
  [file join $root rtl capture_unit.sv] \
  [file join $root rtl mul_u.sv] \
  [file join $root rtl detector_core.sv] \
  [file join $root rtl detector_top.sv] \
  [file join $root rtl detector_syn_top.sv]]
read_xdc -mode out_of_context [list [file join $root syn constraints.xdc]]  ;# list: path has spaces

synth_design -top detector_syn_top -part $part -mode out_of_context
report_utilization -file [file join $build utilization_synth.rpt]
opt_design
place_design
route_design
report_utilization -file [file join $build utilization.rpt]
report_utilization -hierarchical -file [file join $build utilization_hier.rpt]
report_timing_summary -max_paths 5 -file [file join $build timing.rpt]
report_power -file [file join $build power.rpt]
report_drc -file [file join $build drc.rpt]
report_methodology -file [file join $build methodology.rpt]
