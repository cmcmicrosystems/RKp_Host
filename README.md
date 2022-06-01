# RKp_Host

Host side PC application software

# Design requirements

# Design decisions

Use JSON as format to store and load data to hard drive.

- Opposite to CSV or "multiple files in a folder", JSON is more flexible.
- It will be easier to implement backward compatibility between multiple versions of a program.
- In the future it may be required to support multiple electrodes, recording of temperature,
  or other telemetry at the same time.
- Moreover, format needs to support both square wave voltammograms and whole spectrum voltammograms, possibly at the
  same time.
- Storage of non-tabular data at varying bit-rates.

# Known errors

> 'NoneType' object is not callable

Debugger doesn't work on Python 3.10 correctly, so use 3.9 instead.

More info:
https://youtrack.jetbrains.com/issue/PY-52137