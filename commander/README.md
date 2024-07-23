
# Post Silicon Testing

This directory contains various files used when testing the silicon after it
was manufactured and returned.

So far the silicon tested seems to exactly replicate the original
pre-synthesis and post-implementation (gate-level) simulation.

To assist quickly getting started the `repl.py` script is provided, please
read the instruction in the top of the file on how to use it.

Should you want to see how this might look when it is working correctly
a `minicom.cap.txt` file is provided showing the whole process used which
includes at the end a number of tests included inside `repl.py`.

Take a look at https://commander.tinytapeout.com/ with Chrome web browser
(due to needing WebUSB support).  Which is based on the project at
https://github.com/TinyTapeout/tt-commander-app for quick access.

---

I am currently working on a project that will allow the original cocotb
testbench to be run against the silicon (at reduced clock speed, or maybe
nearer original pre-synth simulation full speed if an FPGA is used
connected to the TT PCB PMODs).
