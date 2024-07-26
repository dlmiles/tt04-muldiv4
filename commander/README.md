
# Post Silicon Testing

This directory contains various files used when testing the silicon after it
was manufactured and returned mounted on carrier board with the TT04 PCB.

So far the silicon tested seems to exactly replicate the original
pre-synthesis and post-implementation (gate-level) simulations.

To assist quickly getting started the `repl.py` script is provided, please
read the instructions at the top of the file on how to use it.

Should you want to see how this might look when it is working correctly
a `minicom.cap.txt` file is provided showing the whole process used which
includes the 'ALL TESTS PASS' result after running a number of tests
included inside `repl.py`.

Please try to break it and report any issues.

Take a look at https://commander.tinytapeout.com/ with Chrome web browser
(due to needing WebUSB support).  Which is based on the project at
https://github.com/TinyTapeout/tt-commander-app for quick access.

See also [pyttloader Utility](pyttloader/)

---

## Using minicom

Linux has minicom a long standing VT100 style serial port terminal designed for
use from a shell command line.  If some part of this diagnostic process is not
working for you, an Internet search to resolve the item for your Linux
distribution choice and PC hardware maybe needed.

```
# Install lsusb and minicom (assumes debian/ubuntu package naming)
sudo -E apt-get install usbutils minicom

# Summary of all USB devices visible on physical bus
lsusb

# Looking for RP2040 uPython see iManufacturer field in output
lsusb -d 2e8a:0005 -v

# This provides access to kernel logging data that might assist confirming
# detection when the device is physically plugged/unplugged.
dmesg | egrep "(usb [0-9]|ttyACM)" | tail -n 16

# Check to see the system has kernel CDC driver loaded and active by default
lsmod | grep cdc
cdc_acm                32768  2

# Check to see if the system already has a serial device automatically created
#  using above kernel driver after USB physical device connection is made.
# This file may appear and disappear dynamically due to 'udev' automatically
#  managing USB hotplug devices.
ls -l /dev/ttyACM*
crw-rw----. 1 root dialout 166, 0 Jul 23 21:12 /dev/ttyACM0

# Check you have permission to the ugo group to access, in this case 'dialout'
#  your Linux distribution group naming and hotplug device security may vary.
id
uid=424242(user) gid=424242(user) groups=424242(dlm),10(wheel),18(dialout)

# Minicom can be a little quirky if you are not used to it and maybe
#  configured by default to assume ATDT style modem control to perform
#  dial out.
# So the following command line might provide a good starting point to
#  reduce first time quirks.
# When it loads into menu you can use "Exit" to exit the menu to go into
#  terminal mode to interact with MicroPython and should get to see error
#  messages on screen if there was a problem.
minicom -D /dev/ttyACM0 --noinit --wrap -C my_session_capture.txt --setup

# Once inside the following key sequences should get you started:
#  Ctrl-A then Ctrl-Z  (for the help menu)
#  Ctrl-A then Ctrl-O  (for the setup menu, to set device/speed/vitals)
#  Ctrl-A then Ctrl-Y  (select and paste/upload raw a file, quirky UI)
#  Ctrl-A then Ctrl-X  (to exit)

# The -C option will be recording your session by default to a local file

# If you tap <RETURN> you expect to see ">>" from MicroPython in response.
# If the project seems active (running factory QA testing diagnostics) due
#  to default configuration in firmware inside config.ini then you can issue
#  these 2 commands to reset at anytime:
machine.reset()
# This will temporarly disconnect '/dev/ttyACM0' and autoreconnect.
tt.project_clock_stop()  # stopClocking()
# This will halt the active clock that if running.

# You can now work inside minicom interacting with MicroPython.

# Ctrl-A then Ctrl-X then "Exit" to exit minicom.
# Once back at the command prompt it is sometimes needed to fix the console
#  when it exit back to shell without restoring text mode terminal settings.
reset
```

---

# Using Windows and PuTTY

Many of the features of minicom also exist in parallel using PuTTY GUI this
maybe an especially good option for Windows systems.

WindowsKey and S = To enter system search
"Device Manager" is the term to search for, this should find the local operating
system utility installed on every standard Windows systems.
When Device Manager is open, look in the device tree for "Ports (COM & LPT)"
this will be present in the top level, if this node is not seen this suggests
a problem with USB connection and detection.  Some security controlled
environments (such as corporate issued laptops) might have security software
restricting the kinds of USB devices can be attached and used.  For example
Keyboard/Mouse maybe allowed but USB Storage/Key or unexpected devices maybe
denied, making the operating system ignore their presense even when
connected and functioning correctly.
Inside the "Ports (COM & LPT)" node will be: USB Serial Device (COMx)
The COM99 number is dynamically generated and needs to be known before you
can configure PuTTY to connect (see below).

Download and run PuTTY https://www.putty.org/ .
On the PuTTY Configuration window (the main dialog that should open on use)
in the (Category -> Session) you need to select:
 * Connection Type = Serial
 * Serial line = COMxx
 * Speed = 9600 (any default speed should do)
 * You can now click [Open] button to proceed.
You need to modify COMxx with the number you saw from Device Manager.

Once connected you should be able to interact with MicroPython.

---

I am currently working on a project that will allow the original cocotb
testbench to be run against the silicon (at reduced clock speed, or maybe
nearer original pre-synthesis simulation speed if an FPGA is used
connected to the TT PCB PMOD via USB).  Then maybe this can lead into
performing lock-step style validation, which can use test-benches that can
be more reactive and random (in lock-step the original iverilog/verilator
simulator runs in parallel and lock-step with the silicon running the same
inputs, trying to observe and find a discrepency, indicating a simulation
modelling error, manufacturing defect, or a bug in the testing system).
