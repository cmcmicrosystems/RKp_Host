# RKp_Host

<u> Work in progress. </u>

Host side PC application software

# Design requirements


# Design decisions

Use JSON as format to store and load data to hard drive.
In the future, if RAM consumption becomes an issue, use 'dask dataframe', 'shelve', 'klepto', etc. 
to save data to hard drive while keeping cache(?) in RAM, if all data does not fit in RAM at once.

- Opposite to CSV or "multiple files in a folder", JSON is more flexible.
- It will be easier to implement backward compatibility between multiple versions of a program.
- In the future it may be required to support multiple electrodes, recording of temperature,
  or other telemetry at the same time.
- Moreover, format needs to support both square wave voltammograms and whole spectrum voltammograms, possibly at the
  same time.
- Storage of non-tabular data at varying bit-rates.

# Setup environment:
Use Python 3.9 or 3.10, you can get it from https://www.python.org/downloads/

Or use Anaconda

Or virtual environment

After installation, run the following command:
> $ pip install -r requirements.txt
 
As IDE use PyCharm or VSCode

# Tested with:
- Computer: HP EliteBook 850 G5
- CPU: Intel(R) Core(TM) i7-8550U CPU @ 1.80GHz   1.99 GHz
- RAM: 8 GB
- Edition: Windows 11 Pro
- Version: 21H2
- OS build: 22000.675
- Experience: Windows Feature Experience Pack 1000.22000.675.0

- IDE: PyCharm 2022.1.2 (Professional Edition)
- 
- Latest driver updates(Bleak had some problems connecting while using old drivers, updates solved issue)

# Run the application:

Double-click on the icon (in Windows), or open the file in a terminal window.
> $ python release1.py

# Known errors

> 'NoneType' object is not callable

Debugger doesn't work on Python 3.10 correctly, so use 3.9 instead.

More info:
https://youtrack.jetbrains.com/issue/PY-52137