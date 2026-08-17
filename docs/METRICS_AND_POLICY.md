# Metrics, missing data and action policy

The archive minimises a vector, not a weighted scalar. Latency is divided by the first successfully
verified baseline latency. Area is the maximum fraction used among LUT, FF, DSP, BRAM and URAM,
using capacities from `task.json`. If measured power is present, power is divided by baseline power
and the candidate enters the three-objective archive; otherwise it enters a separate two-objective
latency-area archive. Missing power is never replaced with `1` and two- and three-dimensional points
are never compared. The default normalised hypervolume reference is `(1.5, 1.0, 1.3)`; points outside
it contribute zero, and each experiment must report any task-specific change to that reference.

For each `(phase, failure class, action)` tuple, success probability is the posterior mean of a
Beta(1,1) Bernoulli model. Utility is an exponentially weighted moving average (EWMA) of non-negative
hypervolume improvement; risk is an EWMA of timeout, tool-crash or killed-process indicators. The
selection score is `probability * utility / (credit_cost * (1 + risk))`. Priors, every decision and
every update are written to the trace, so the value-per-credit choice can be reconstructed.
