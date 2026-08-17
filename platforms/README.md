# Platform integration

HLS source alone cannot create a working bitstream: the design also needs board interfaces,
clocks, memory connections, constraints and a host program. Copy `example/task-fragment.json` into
a task configuration and replace the two scripts with platform-specific commands.

The implementation command must perform Vivado synthesis, placement and routing and write a JSON
object using the `PPAMetrics` field names. At minimum it should report `latency_cycles`, `clock_ns`,
`lut`, `ff`, `dsp`, `bram`, `uram`, and `timing_slack_ns`; add `power_w` only when it comes from a
named report or measurement method. The hardware command must program the named board, execute
known input/output vectors, and write the same JSON contract. A non-zero process exit means failure.

`scripts/run_board_benchmark.py` can aggregate cycle-counter results, but the board-specific runner
must be written for the chosen platform and must obtain its count from hardware. Host wall-clock
time is not silently relabelled as FPGA latency.
