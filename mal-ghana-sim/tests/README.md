# mal-ghana-sim tests

The F1.e parity test (`test_abm_fast_parity.py`) has been removed.
Python↔C++ parity is now validated by the calibration scorers
(10 scorers + LLM verdict in `mal-core/src/mal_core/abm/tests/calibration/`).
