
(venv) $ ./pyttloader/pyttloader.py --help
usage: pyttloader [-R | --machine-reset | --no-machine-reset] [--capture-write | --no-capture-write] [--capture-mode int_value] [--capture | --no-capture] [-C [capturefile]]
                  [-D [PORT]] [-q] [-?] [-v] [-V]
                  uploadfile [sendexpect ...]

TinyTapeout MicroPython load and runner

positional arguments:
  uploadfile            The MicroPython program to upload
  sendexpect            Send/Expect scripts NOIMPL

options:
  -R, --machine-reset, --no-machine-reset
                        Perform machine.reset()
  --capture-write, --no-capture-write
                        Capture Output Data [Off]
  --capture-mode int_value
                        Capture Mode Mask 0-31 [1]
  --capture, --no-capture
                        Capture Enable [On]
  -C [capturefile], --capture-file [capturefile]
                        Capture file [capture.txt]
  -D [PORT], --device [PORT]
                        Serial device [auto-detect]
  -q, --quiet           Set verbose level to 0
  -?, -h, --help        Show help message
  -v, --verbose         Increase verbosity
  -V, --version         show program's version number and exit

https://github.com/dlmiles/tt04-muldiv4/tree/main/commander/pyttloader
