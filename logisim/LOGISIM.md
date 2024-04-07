
# Logisim Evolution details

This project was originally started as a hand crafted digital logic
schematic in logisim-evolution for each of the main parts.  A multiplier and a divider.

Version: v3.9.0dev

Project page: https://github.com/logisim-evolution/logisim-evolution

Download details: https://github.com/logisim-evolution/logisim-evolution?tab=readme-ov-file#download

## Visuals

* [Multiplier implementation](https://raw.githubusercontent.com/dlmiles/tt04-muldiv4/main/docs/LOGISIM_Multiplier_View.png)
* [Multiplier testing (animated)](https://raw.githubusercontent.com/dlmiles/tt04-muldiv4/main/docs/TT04_325_MULDIV4_LOGISIM_MULTIPLY_TESTING.gif)
* [Multiplier fly around (animated - jiterty needs reworking)](https://raw.githubusercontent.com/dlmiles/tt04-muldiv4/main/docs/TT04_325_MULDIV4_LOGISIM_MULTIPLY_WORKING.gif)
* [Divider implementation](https://raw.githubusercontent.com/dlmiles/tt04-muldiv4/main/docs/LOGISIM_Divider_FourBit_Implementation.png)
* [Divider testing (animated)](https://raw.githubusercontent.com/dlmiles/tt04-muldiv4/main/docs/TT04_325_MULDIV4_LOGISIM_DIVIDER_TESTING.gif)
* [Full Adder Circuit](https://raw.githubusercontent.com/dlmiles/tt04-muldiv4/main/docs/LOGISIM_Full_Adder_Circuit.png)
* [Half Adder Circuit](https://raw.githubusercontent.com/dlmiles/tt04-muldiv4/main/docs/LOGISIM_Half_Adder_Circuit.png)
* [Divider Unit (FA with MUX bypass A to SUM)](https://raw.githubusercontent.com/dlmiles/tt04-muldiv4/main/docs/LOGISIM_DIVUNIT.png)

## How to export

Logisim has built in functionality to export the design to a set of project files that
target a particular toolchain environment and FPGA hardware.  This functionality can be
used to generate the verilog files that can be found checked into the src/ directory of
this git project.

This functionality seemed to be a little quirky to use, the progress did not seem to get
to a completed state (with a progress bar stuck indicating it is still working on the file
generation), but the files did get created and I could tweezer out the verilog modules
produces and copy into this project.

Then I create a top*.v wrapper to make the external interface match the TinyTapeout project
(user module) interface and other various verilog shim modules to try to reuse what
was exported verbatim and manage any differences in these additional files.  This would
allow a fresh export process to be used as-is to help with the development cycle.

    Menu Bar -> FPGA -> Synthesis & Download
        Target board: Spartan 3E Starter (I picked an option I had some familiarity)
        Toplevel: main
        Clock settings: (almost any value should do, this is non-clocked project)
            Freq: 1.0 Hz
            Divider: 25000000
        Action Method:
            Generate HDL Only
            Click: Execute (click this button to perform the export)

## How to test

In the logisim design you will find additional logisim components such as
a memory and logic-analyser display, counter, comparators and pass/fail
status light.  As well as a latching fail light.

These items were used to help automate the testing inside logisim.

The expected input and output data was generated using variations of the
Perl script in this folder.  If you re-use you will need to check over
the output and tweak calculations as necessary.

This generates a memory image file in logisim's native format that can be
loaded into the memory component found inside the designs.  This can be done
with a right-click action on the component.

### Example testing of multipler

Ensure the input pins A0 through A3 and B0 through B3 are disconnected (wires cut short)
and that the `Tunnel` (a logicsim component construct) labled `A` and `B` are wired into
the input lines.

Then set the `OP_SIGNED` input pin for the mode of operation.

Reset Simulation (Ctrl-R)

Manual Step (Ctrl-T) or Autotick toggle (Ctrl-K).

Then inspect the `Tunnel` labeled `R` in the logic analyser, it should always have a 1
state indicating the output value matches the expected output value that is loaded into
the hex memory.

## Erratum

There maybe a mismatch with the name of some HA and FA module between the verilog
and the current logisim schematic.  This was a correction made after the TT04
submission deadline.

* HA_P0A0B1 -> HA_P1A0B1
* FA_P1A1B1 -> FA_P2A1B1
* HA_P1A0B2 -> HA_P2A0B2
