![](../../workflows/gds/badge.svg) ![](../../workflows/docs/badge.svg) ![](../../workflows/test/badge.svg)

# TT04 Multiply and Divide Unit <br>(4-bit x 4-bit, signed/unsigned)

This is my TinyTapeout 04 submission which will see this digital logic circuit design
fabricated into a computer chip (ASIC) using the SKY130 process node.

This project was originally developed using schematics drawn with [logisim-evolution](logisim/LOGISIM.md)
using discrete logic elements (AND/OR/XOR/NOT/NAND gates and MUX2).  See
also this link for some visuals of the circuit.

Github Actions include:
 * Pre-synthesis simulation testing
 * Post-implemenetation (gate-level) simultation testing

Useful links
 * [Github Pages](https://dlmiles.github.io/tt04-muldiv4/)
 * [Tiny Tapeout 4 project ID#325 information ](https://tinytapeout.com/runs/tt04/325/)
 * [Tiny Tapeout 4 shuttle information ](https://tinytapeout.com/runs/tt04/)

## MULDIV4 Peripheral

The unit is a combinational logic project.  So there is no need to provide a clock input.

Apply the appropiate states to the input data pins and after propagration delays
(estimated to be in the order of nano-seconds) you should be able to observe the computed
result at the output pins of the IC.


The two main modes of operation:

### Multipler

The multiplier logic method uses Ripple Carry Array as 'high speed multiplier' topology.

| Pin         |     | Function         | Notes                                       |
|:------------|----:|:-----------------|:--------------------------------------------|
| UIO_IN[6]   |  IN | OPSIGNED bit     | 0=unsigned, 1=signed                        |
| UIO_IN[7]   |  IN | MULDIV Mode bit  | 0=multiply (always for Multiply operations) |
| UI_IN[3:0]  |  IN | Multiply input A | Multiplicand input data 4-bits wide         |
| UI_IN[7:4]  |  IN | Multiply input B | Multiplier input data 4-bits wide           |
| UO_OUT[7:0] | OUT | Product output   | The result is 8-bits wide                   |
| UIO_OUT[4]  | OUT | Not Applicable   | Ignore state                                |
| UIO_OUT[5]  | OUT | Not Applicable   | Ignore state                                |

### Divider

The divider logic method uses Full Adder with Mux as 'combinational restoring array divider algorithm'

All error bit indicators (active high) take precedence over any Quotient or Remainder result shown.

| Pin         |     | Function         | Notes                                   |
|:------------|----:|:-----------------|:----------------------------------------|
| UIO_IN[6]   |  IN | OPSIGNED bit     | 0=unsigned, 1=signed                    |
| UIO_IN[7]   |  IN | MULDIV Mode bit  | 1=divide (always for Divide operations) |
| UI_IN[3:0]  |  IN | Dividend input   | Dividend input data 4-bits wide         |
| UI_IN[7:4]  |  IN | Divisor input    | Divisor input data 4-bits wide          |
| UO_OUT[3:0] | OUT | Quotient output  | Quotient result is 4-bits wide          |
| UO_OUT[7:4] | OUT | Remainder output | Remainder result is 4-bits wide         |
| UIO_OUT[4]  | OUT | EOVERFLOW        | Overflow error indicator when set       |
| UIO_OUT[5]  | OUT | EDIV0            | Divide-By-Zero error indicator when set |


---

# What is Tiny Tapeout?

TinyTapeout is an educational project that aims to make it easier and cheaper than ever to get your digital designs manufactured on a real chip!

Go to https://tinytapeout.com for instructions!

## How to change the Wokwi project

Edit the [info.yaml](info.yaml) and change the wokwi_id to match your project.

## How to enable the GitHub actions to build the ASIC files

Please see the instructions for:

- [Enabling GitHub Actions](https://tinytapeout.com/faq/#when-i-commit-my-change-the-gds-action-isnt-running)
- [Enabling GitHub Pages](https://tinytapeout.com/faq/#my-github-action-is-failing-on-the-pages-part)

## How does it work?

When you edit the info.yaml to choose a different ID, the [GitHub Action](.github/workflows/gds.yaml) will fetch the digital netlist of your design from Wokwi.

After that, the action uses the open source ASIC tool called [OpenLane](https://www.zerotoasiccourse.com/terminology/openlane/) to build the files needed to fabricate an ASIC.

## Resources

- [FAQ](https://tinytapeout.com/faq/)
- [Digital design lessons](https://tinytapeout.com/digital_design/)
- [Learn how semiconductors work](https://tinytapeout.com/siliwiz/)
- [Join the community](https://discord.gg/rPK2nSjxy8)

## What next?

- Share your GDS on Twitter, tag it [#tinytapeout](https://twitter.com/hashtag/tinytapeout?src=hashtag_click) and [link me](https://twitter.com/matthewvenn)!
