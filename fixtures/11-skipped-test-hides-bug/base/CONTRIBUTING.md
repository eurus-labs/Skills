# Contributing

`make test` runs the fast tests. Slow tests are skipped unless `RUN_SLOW=1`; CI always sets it.
A change is ready to merge only when `RUN_SLOW=1 make test` passes.
