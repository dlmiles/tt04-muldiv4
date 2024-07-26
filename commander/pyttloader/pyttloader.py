#!/usr/bin/env python3
#
#  ./pyttloader.py --machine-reset -D /dev/ttyACM0 repl.pl
#
#  A utility to help automate command line development/testing/running
#  of repl.py scripts into MicroPython.  There are probably a number of
#  other options around for the script uploading part but this is more
#  a playground to understand better the considerations when working with
#  standard MicroPython specifically in the TT PCB implementation.
#
#
#
#  TODO 
#       use non-blocking API from python, while the pySerial is using
#        non-blocking at low level it does not provide a rich API at
#        the application end to mix-and-match (blocking, timed-blocking,
#        full-duplex-event-loop with independant semi-automatic management
#        of flushing).  MOSTLY DONE NOW
#       build Exception listener channel (at the moment you need to read
#        the capture_file)  TODO
#       using standard logger and --verbose
#
#	take a look at removing the _or_exit() naming suffix maybe it is
#	 just the default as we are timeout/deadline based
#
#       I have a C/C++ version of something similar that can fully manage
#        the USB and provide user-space USB host CDC driver (which I am
#        looking to add a custom USB interface extentions for TT).
#       The C/C++ version will have language bindings back to Python and
#        Java and I expect in the distant future
#
#
# Copyright (c) 2024 Darryl L. Miles
# SPDX-License-Identifier: Apache-2.0
#
#
import os
import sys
import time
from numbers import Number
from typing import Type
from enum import Enum
import argparse
import serial

# Not used
PROJECT_EDITION = "tt04"
PROJECT_ADDRID  = "325"


# This gets visibility of a data stream (all inbound data) then tries to apply
#  hieuristics to detect if a Python exception report occured, or maybe which
#  prompt mode the REPL is in.
class InboundDataFilter():
    def __init__(self, *args, **kwargs):
        self._data = bytearray()
        self.reset()


    def data_in(self) -> None:
        # FIXME the work happens here
        pass


    def reset(self) -> None:
        self._seen_exception = False
        self._exception = []


    @property
    def is_error(self) -> bool:
        return self._seen_exception


# Refactored capture to file implementation
class Capture():
    def __init__(self, *args, **kwargs):
        self._fh = None
        self._capture_read = True
        self._capture_write = True # tool default is False here


    def capture_rename(self, path: str) -> bool:
        if os.path.isfile(path):
            path_old = path + ".old"
            if os.path.isfile(path_old):
                os.unlink(path_old) # maybe Windows needs this first
            return os.rename(path, path_old) # best-effort rename
        return False


    def set_capture_file(self, path: str, capture_write: bool = True) -> bool:
        if path is None or len(path) == 0:
            return False
        self.close()
        self.capture_rename(path)
        self._fh = open(path, "wb")
        assert self._fh is not None
        self.capture_write = capture_write
        #print(f"set_capture_file({path}, {capture_write})")
        return True


    def write(self, *args) -> None:
        if not self._fh:
            return
        for v in args:
            if v is not None:
                self._fh.write(v)


    def data_in(self, *args) -> None:
        if not self.capture_read:
            return
        self.write(*args)


    def data_out(self, *args) -> None:
        if not self.capture_write:
            return
        self.write(*args)


    def comment(self, *args) -> None:
        self.write(*args)


    def close(self) -> None:
        if self._fh:
            self._fh.close()
            self._fh = None


    @property
    def capture_read(self) -> bool:
        return self._capture_read

    @capture_read.setter
    def capture_read(self, v: bool) -> None:
        self._capture_read = v

    @property
    def capture_write(self) -> bool:
        return self._capture_write

    @capture_write.setter
    def capture_write(self, v: bool) -> None:
        self._capture_write = v


# Timeout class that captures and simplifies pySerial timeout model
#  (units in seconds, None means forever, 0 means just/at-least once)
class Timeout():
    def __init__(self, timeout: Number = None, forever: Number = None, at_least_once: bool = True):
        if timeout is None: # allows mitigation of forever request to another value
            timeout = forever
        self._timeout = timeout
        self._first = at_least_once
        self.start()
        if timeout is not None:
            self._expire = self._start + timeout
        else:
            self._expire = None


    def start(self) -> None:
        self._start = time.time()
        return
    

    def has_remaining(self) -> bool:
        if self._first:
            self._first = False
            return True
        if self._expire is None:
            return True
        rem = self.remaining()
        if rem is None or rem > 0:
            return True
        return False


    def remaining(self) -> float:
        if self._expire is None:
            return None
        return self._expire - time.time()


    def raise_if_expired(self, *args) -> None:
        if self.has_remaining():
            return
        if len(args) > 0:
            raise Exception(*args)
        else: # use a default message
            raise Exception(f"raise_if_expired(timeout={self._timeout} expire={self._expire} remaining={self.remaining()})")


# Heavy lifting class for reimplementing read_until function
class BinaryMatcher():
    def __init__(self, pattern: bytes):
        self.reset(pattern)


    def reset(self, pattern: str) -> None:
        self._pattern = pattern
        self._offset = 0
        self._prefix = None
        self._trailer = None


    # assumes new data starting at offset
    def match(self, data: bytes, offset: int = 0, trailer: bool = False) -> bool:
        assert self._pattern is not None
        pattern = self._pattern
        plength = len(pattern)
        po = self._offset

        #print(f"match(data={len(data)}, offset={offset}) pat={pattern} po={po} pfx={self._prefix}")

        if self._prefix is not None:
            alldata = self._prefix + data[offset:]
            pfxlength = len(self._prefix)
            assert po <= len(self._prefix), f"po <= len(self._prefix) {po} <= {len(self._prefix)}"
        else:
            alldata = data[offset:]
            pfxlength = 0

        dlength = len(alldata)

        do = 0 # offset # if offset < dlen
        while po < plength and (do+po) < dlength:
            if alldata[do+po] != pattern[po]:
                po = 0
                do += 1
                continue
            #print(f"match(do={do}, po={po})")
            po += 1

        ret = po == plength

        if ret:
            self._data_before_match = alldata[0:do] # FIXME make on demand
            self._match_pattern = pattern
            self._match_length = plength
            self._match_start = do - pfxlength
            self._match_end = do + plength - 1 - pfxlength
            self._match_resume = do + plength - pfxlength
            self._data_after_match = alldata[do+plength:] # FIXME make on demand

        if trailer: # by default we only store match window not all data since last match
            if ret:
                self._trailer = alldata[do+plength:]
            else:
                self._trailer = alldata

        if ret:
            self._offset = 0
            self._prefix = None
        else:
            self._offset = po
            self._prefix = None if do == dlength else alldata[do:]
        self._start = do
        #print(f"match(po={po}, prefix={self._prefix}, do={do}) SAVE")

        return ret


    def trailer(self) -> bytes:
        return self._trailer


    @property
    def pattern_offset(self) -> int:
        return self._offset


    @property
    def pattern_remaining(self) -> int:
        rem = len(self._pattern) - self._offset
        assert rem >= 0
        return rem


    def data_before_match(self) -> bytes:
        return self._data_before_match


    def data_before_with_match(self) -> bytes:
        return self._data_before_match + self._match_pattern


    def match_start(self) -> int:
        return self._match_start


    def match_end(self) -> int:
        return self._match_end


    def match_pattern(self) -> bytes:
        return self._match_pattern


    def match_length(self) -> int:
        return self._match_length


    def match_resume(self) -> int:
        return self._match_resume


    def data_after_match(self) -> bytes:
        return self._data_after_match


    def data_after_with_match(self) -> bytes:
        return self._match_pattern + self._data_after_match




class MySerial(serial.Serial):
    ENCODING = "utf-8"
    DEFAULT_TIMEOUT = 10.0
    EOL = "\r\n"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._portname = kwargs['port']
        
        self._capture = Capture()

        self._fh = None
        self._capture_read = True
        self._capture_write = False


    def encode(self, v: str) -> bytes:
        return v.encode(self.ENCODING)


    # My attempt to provide non-blocking version of Serial.read(int)
    def read_nb(self, size: int = 1) -> bytes:
        saved_timeout = self.timeout        
        self.timeout = 0 # docs say this makes it non-blocking
        data = self.read(size)
        self.timeout = saved_timeout
        return data


    # My attempt to provide limited time block version of Serial.read(int)
    # timeout: Number = INHERIT ## should be the default, only if kwargs is specific does it change
    def read_timo(self, size: int = 1, timeout: Number = 0, minreadlen: int = None) -> bytes:
        if minreadlen is None:
            minreadlen = size

        data = None
        saved_timeout = self.timeout

        t = Timeout(timeout)

        left = minreadlen
        while t.has_remaining() and left > 0: # do while
            self.timeout = t.remaining()

            if data is None:
                readlen = size
            else:
                readlen = size - len(data)
            
            readlen = min(readlen, left)

            if readlen <= 0: # size goal is met
                break

            # Hmm really want API with a minreadlen=1 maxreadlen=readlen
            #  so instead we have to compute readlen above
            databytes = self.read(readlen)

            if databytes:
                if data is not None:
                    data += databytes
                else:
                    data = databytes
                left -= len(databytes)

        self.timeout = saved_timeout
        return data


    # drain with capture
    def drain_input(self, timeout: Number = 0) -> int:
        # FIXME timeout==0 means non-blocking
        # Hmm self.readable() doesn't seem to mean, at the last select() was it marked readable
        drain_count = 0
        while True: # should probably attach loop limit
            readlen = self.in_waiting
            if readlen <= 0:
                break
            databytes = self.read_nb(size=readlen)
            self._capture.data_in(databytes)
            if databytes:
                drain_count += len(databytes)

        if timeout > 0:
            t = Timeout(timeout, forever = 0) # treat forever as run-once
            while t.has_remaining(): # do while
                databytes = self.read_timo(size=256, timeout=t.remaining())
                self._capture.data_in(databytes)
                if databytes:
                    drain_count += len(databytes)

        # One last read of whatever is in the queue
        if self.in_waiting > 0: # should probably attach loop limit
            readlen = self.in_waiting
            databytes = self.read_nb(size=readlen)
            self._capture.data_in(databytes)
            if databytes:
                drain_count += len(databytes)

        return drain_count


    def write(self, *args, capture: bool = True) -> int:
        data = bytearray(0)
        for v in args:
            if type(v) is bytes or type(v) is bytearray:
                data += v
            elif type(v) is str:
                data += self.encode(v)
            else:
                data += self.encode(str(v))
        if capture:
            self._capture.data_out(data)
            print(f">>> {str(data, self.ENCODING).rstrip()}")
        super().write(data)
        return len(data)


    def writeline(self, *args, capture: bool = True) -> int:
        data = bytearray()
        for v in args:
            if type(v) is bytes or type(v) is bytearray:
                data += v
            elif type(v) is str:
                data += self.encode(v)
            else:
                data += self.encode(str(v))
        data += self.encode(self.EOL)
        if capture:
            self._capture.data_out(data)
            print(f">>> {str(data, self.ENCODING).rstrip()}")
        super().write(data)
        return len(data)


    # Serial.read_until is useful but we ideally want to specify, until/continue minread, maxread, timeout/nonblock per call
    # until/continue means the function of pattern matching is reset or resumes
    # the minreadlen/maxreadlen controls if we should wait timeout
    # minreadlen: int = None ## didn't find a use for this here, turns out it is needed at read_timo()
    def my_read_until(self, pattern: bytes, maxreadlen: int = None, timeout: Number = None) -> bytes:
        assert maxreadlen is None or maxreadlen > 0
        assert timeout is None or timeout >= 0

        if pattern is None: # resume
            matcher = self._matcher
            assert type(matcher) is BinaryMatcher # must be something to resume
        else:
            assert type(pattern) is bytes
            matcher = BinaryMatcher(pattern) # all the heavy lifting here
            self._matcher = matcher

        t = Timeout(timeout)

        # timeout, once or non-blocking
        data = bytes()
        while t.has_remaining(): # do while
            pleft = matcher.pattern_remaining # pattern bytes left
            if maxreadlen:
                readlen = max(pleft, maxreadlen)
            else:
                readlen = pleft

            #print(f"read_timo(size={readlen}, timeout={t.remaining()})")
            databytes = self.read_timo(size=readlen, timeout=t.remaining(), minreadlen=pleft)
            #print(f"read_timo(size={readlen}, timeout={t.remaining()}) = {databytes}")
            if databytes:
                if data is not None:
                    data += databytes
                else:
                    data = databytes

            # try to match pattern
            if matcher.match(data):
                break

        return data


    def wait_for_pattern(self, pattern: str, timeout: int = DEFAULT_TIMEOUT, endswith = False) -> bool:
        t = Timeout(timeout)
        find = self.encode(pattern)
        alldata = bytearray()
        while t.has_remaining():
            # read_until is useful but we ideally want to specify, until/continue minread, maxread, timeout/nonblock per call
            # until/continue means the function of pattern matching is reset or continues
            readlen = len(find)
            databytes = self.my_read_until(find, maxreadlen=readlen, timeout=t.remaining())
            #databytes = self.read_until(find, readlen)
            self._capture.data_in(databytes)
            alldata += databytes
            #print(f"read_until={len(databytes)} \"{pretty(str(databytes, self.ENCODING))}\"")
            if endswith and alldata.endswith(find):
                return True
            elif str(alldata, self.ENCODING).find(pattern) >= 0:
                return True
        # diagnostic info on failure to match
        print(f"DEBUG1: Had data: {len(alldata)} {alldata[-40:]}")
        print(f"DEBUG2: Had data: {len(alldata)}")
        return False


    def wait_for_prompt_or_exit(self, timeout: int = DEFAULT_TIMEOUT, sendcr = False) -> bool:
        if sendcr:
            self.writeline()
        PROMPT_PATTERN = ">>> "
        if self.wait_for_pattern(PROMPT_PATTERN, timeout = timeout, endswith = True):
            return True
        print(f"ERROR: Timeout waiting for prompt=\"{PROMPT_PATTERN}\"", file=sys.stderr)
        sys.exit(1)


    def wait_for_or_exit(self, pattern: str, timeout: int = DEFAULT_TIMEOUT) -> bool:
        if self.wait_for_pattern(pattern, timeout = timeout):
            return True
        print(f"ERROR: Timeout waiting for pattern=\"{pattern}\"", file=sys.stderr)
        sys.exit(1)


    # This will attempt to auto-detect the remote state and recover MicroPython REPL prompt
    def recover_prompt_or_exit(self, timeout: int = DEFAULT_TIMEOUT) -> bool:
        self.writeline()
        PROMPT_PATTERN1 = ">>> " # FIXME move to input data observer
        PROMPT_PATTERN2 = "... "
        PROMPT_PATTERN3 = "=== "
        t = Timeout(timeout)
        pattern1 = self.encode(PROMPT_PATTERN1)
        pattern2 = self.encode(PROMPT_PATTERN2)
        pattern3 = self.encode(PROMPT_PATTERN3)
        alldata = bytearray()
        while t.has_remaining():
            databytes = self.read_until(self.encode(" "), size=4)
            self._capture.data_in(databytes)
            alldata += databytes
            #print(f"read_until={len(databytes)}")
            if alldata.endswith(pattern1):
                return True
            elif alldata.endswith(pattern2): # Nesting mode
                self.write(b'\003')
            elif alldata.endswith(pattern3): # Ctrl-E mode
                self.write(b'\003')
        print(f"ERROR: Timeout trying to recover MicroPython prompt, try resetting device.", file=sys.stderr)
        sys.exit(1)


    def wait_for_disconnect_and_reconnect_or_exit(self, timeout: int = DEFAULT_TIMEOUT) -> bool:
        t = Timeout()
        while t.has_remaining():
            try:
                databytes = self.read(size=4096)
                self._capture.data_in(databytes)
                if not self.is_open:
                    break
            except serial.SerialException as ex:
                # device reports readiness to read but returned no data (device disconnected or multiple access on port?)
                if str(ex).find("device disconnected") >= 0:
                    self.close(close_fh=False) # super().close()
                self._capture.comment(self.encode(f"{self.EOL}DISCONNECTED{self.EOL}"))
                print(f"=== DISCONNECTED")
                break

        if self.is_open:
            raise Exception(f"Did not see diconnection within timeout={timeout} now={time.time()}")

        time.sleep(0.330) # a minimum delay to ensure old device disappears

        while t.has_remaining():
            if os.path.exists(self._portname):
                break
            time.sleep(0.1)
        if not os.path.exists(self._portname):
            raise Exception(f"Saw disconnect but new device did not appear timeout={timeout}")

        time.sleep(0.330) # minimum delay to ensure new device appears

        while t.has_remaining():
            try:
                self.open()
                if self.is_open:
                    break
                time.sleep(0.1)
            except serial.SerialException:
                time.sleep(0.1)
            except FileNotFoundError:
                time.sleep(0.1)

        if not self.is_open:
            raise Exception(f"Saw disconnection but could not reconnect within timeout={timeout}")

        self._capture.comment(self.encode(f"RECONNECTED{self.EOL}"))
        print(f"=== RECONNECTED {self._portname}")
        return True

    def replace_binary_line_eol(self, data: bytearray) -> bytearray:
        dlen = len(data)
        # FIXME maybe we should check every char ?
        if dlen > 0 and data[dlen-1] == 0x0a:
            data = data[0:dlen-1] + b'\x0d\x0a'
        return data

    def upload_file(self, path: str, split_on: str = None, capture_mode: int = 0, timeout: int = DEFAULT_TIMEOUT) -> bool:
        t = Timeout(timeout)
        # Maybe this is best in Ctrl-E mode ?  but for that we need state machine
        #   to chunk file and manage indention/detection of an automatic break.
        byte_count = 0
        chunk_count = 0
        drain_count = 0
        file_length = os.path.getsize(path)
        saved_capture_read = self._capture.capture_read
        # FIXME add a filter for pattern detection of incoming data for error handler TraceBack .....Error: ....Exception:
        self._capture.capture_read = (capture_mode & 0x04) == 0x04 # disable during upload ?
        capture_write_data         = (capture_mode & 0x08) == 0x08
        capture_write_control      = (capture_mode & 0x10) == 0x10
        with open(path, "rb") as f:
            print(f"=== UPLOADING: {path} length={file_length}")
            self.write(self.EOL, capture=capture_write_control)
            self.write(b'\005', capture=capture_write_control) # Ctrl-E
            drain_count += self.drain_input()
            while t.has_remaining():
                databytes = f.readline()
                if not databytes:
                    break
                drain_count += self.drain_input()
                if split_on and str(databytes, self.ENCODING).find(split_on) == 0: # start of line
                    self.write(b'\004', capture=capture_write_control) # Ctrl-D
                    self.wait_for_prompt_or_exit(2.5)
                    print(f"\r=== UPLOADING: {path} WORKING {byte_count} CHUNK {byte_count - chunk_count} bytes")
                    chunk_count = byte_count
                    self.write(b'\005', capture=capture_write_control) # Ctrl-E
                    drain_count += self.drain_input()
                byte_count += len(databytes) # before eol replace so the count matches file_length
                databytes = self.replace_binary_line_eol(databytes)
                self.write(databytes, capture=capture_write_data)
                print(f"\r=== UPLOADING: {path} WORKING {byte_count} {drain_count}", end="")
                sys.stdout.flush()
        t.raise_if_expired()
        self.write(b'\004', capture=capture_write_control) # Ctrl-D
        drain_count += self.drain_input(0.15)
        self._capture.comment(self.encode(f"UPLOADING: {path} DONE {byte_count} bytes{self.EOL}"))
        print(f"\r=== UPLOADING: {path} DONE {byte_count} bytes                     ")
        self._capture.capture_read = saved_capture_read # restore
        return True


    def set_capture_file(self, path: str, capture_write: bool = True) -> bool:
        return self._capture.set_capture_file(path, capture_write=capture_write)


    def close(self, close_fh: bool = True) -> None:
        if close_fh:
            self._capture.close()
        super().close()



def quoted(s: str) -> str:
    return '\'' + s + '\''


# Replace control codes with something easier to see
def pretty(input: str) -> str:
    s = ""
    for ch in input:
        c = ord(ch)
        if ch == '\n':
            s += "\\n"
        elif ch == '\r':
            s += "\\r"
        elif ch == '\t':
            s += "\\t"
        elif ch == '\f':
            s += "\\f"
        elif ch == '\v':
            s += "\\v"
        elif c < 32 or c > 127:
            s += f"\\{c:03o}"
        elif ch == '\\':
            s += "\\\\"
        elif ch == '\'':
            s += "\\\'"
        elif ch == '\"':
            s += "\\\""
        else:
            s += ch
    return s


# This is my custom sequence for my project, ideally we want to run this from a seperate
#  execution script (called sendexpect script) of just the commands.  Such a script might
#  want to look like this with UPPERCASE special commands being understood by
#  pyttloader.py as an internal special action and looked up via extensible method name
#  and eval expression.
# RESET()
# UPLOAD("repl.py")
# project325_activate()
# mul_op(1, 8)
# expect('8')
# mul_op(2, 8)
# expect('')
# mul_op(15, 15)
# expect('225')
# div_op(8, 2)
# expect('4')
# div_op(14, 7)
# expect('2')
# div_op(15, 6)
# expect('2r3')
# div_op(15, 0)
# expect('EDIVZERO')
# test()
# expect('SUCCESS: ALL TESTS PASS')
# expect('True')
def run_sequence(comms,
    upload_file: str,
    capture_mode: int,
    machine_reset: bool
    ) -> bool:

    # using comms:
    comms.drain_input()
    comms.recover_prompt_or_exit(timeout=2.5)
    comms.wait_for_prompt_or_exit(sendcr=True)

    if machine_reset:
        comms.writeline(f"machine.reset()")
        comms.wait_for_disconnect_and_reconnect_or_exit(2.5)
        comms.wait_for_or_exit(f"ttboard.boot.rom") # validate we see restart banner
        comms.wait_for_or_exit(f"MicroPython") # validate we see end of restart progress
        comms.wait_for_prompt_or_exit()

    comms.drain_input()
    comms.wait_for_prompt_or_exit(sendcr=True)
    comms.writeline(f"stopClocking() # tt.project_clock_stop()")
    comms.wait_for_prompt_or_exit()
    comms.upload_file(upload_file, '##### SPLIT MARKER #####', capture_mode = capture_mode, timeout = comms.DEFAULT_TIMEOUT * 3)
    comms.writeline()
    comms.wait_for_prompt_or_exit()
    comms.writeline("project325_activate()")
    comms.wait_for_or_exit(f" 325 successfully activated")
    comms.wait_for_prompt_or_exit()
    comms.writeline("mulu_op_status(1, 8)")
    comms.wait_for_or_exit('{}\r\n'.format(quoted('8')))
    comms.wait_for_prompt_or_exit(sendcr=True)
    comms.writeline("mulu_op_status(2, 8)")
    comms.wait_for_or_exit('{}\r\n'.format(quoted('16')))
    comms.wait_for_prompt_or_exit(sendcr=True)
    comms.writeline("mulu_op_status(15, 15)")
    comms.wait_for_or_exit('{}\r\n'.format(quoted('225')))
    comms.wait_for_prompt_or_exit(sendcr=True)
    comms.writeline("mulu_op_status(15, 0)")
    comms.wait_for_or_exit('{}\r\n'.format(quoted('0')))
    comms.wait_for_prompt_or_exit(sendcr=True)
    comms.writeline("divu_op_status(8, 2)")
    comms.wait_for_or_exit('{}\r\n'.format(quoted('4')))
    comms.wait_for_prompt_or_exit(sendcr=True)
    comms.writeline("divu_op_status(14, 7)")
    comms.wait_for_or_exit('{}\r\n'.format(quoted('2')))
    comms.wait_for_prompt_or_exit(sendcr=True)
    comms.writeline("divu_op_status(15, 6)")
    comms.wait_for_or_exit('{}\r\n'.format(quoted('2r3')))
    comms.wait_for_prompt_or_exit(sendcr=True)
    comms.writeline("divu_op_status(15, 0)")
    comms.wait_for_or_exit('{}\r\n'.format(quoted('EDIVZERO')))
    comms.wait_for_prompt_or_exit(sendcr=True)
    comms.writeline("test()")
    comms.wait_for_or_exit("SUCCESS: ALL TESTS PASS")
    # Original version this wouild fail after read_until rewrite that is resolve
    #   and no timeout delays to proceedings
    comms.wait_for_or_exit('True\r\n')
    comms.wait_for_prompt_or_exit(sendcr=True)
    return True


def envname(label: str) -> str:
    return 'SERIAL_' + label.upper()


# FIXME maybe pass Python type (str|int|float|bool|Enum) and have it convert from string or parse-error
def resolve_generic(args, label: str, type: Type = str, default_value: any = None, verbose: bool = True) -> any:
    if args and getattr(args, label, None) is not None:
        print(f"{name} = {value} [using command-line]")
        return getattr(args, label) # command-line takes precedence
    name = envname(label)
    if name in os.environ:
        value = os.getenv(name)
        print(f"{name} = {value} [using environ]")
        return value
    if default_value:
        print(f"{name} = {default_value} [using default]")
    return default_value


def resolve_port(args, label: str, default_value: any) -> str:
    if args:
        port = getattr(args, label, None)
        if port is not None:
            print(f"{label} = {port} [using command-line]")
            return port # command-line takes precedence

    v = resolve_generic(args, label, str, None) # try for option override
    if not v: # naive auto-detect the first file to exist
        for port in ['/dev/ttyACM0', '/dev/ttyACM1']:
            if os.path.exists(port):
                print(f"{envname(label)} = {port} [auto-detected]")
                return port
    return None


def serial_open(args) -> MySerial:
    # Don't expect most of this stuff to really work it was more a sketch
    port = resolve_port(args, 'port', '/dev/ttyACM0')
    baudrate = resolve_generic(args, 'baudrate', int, 115200)
    # can't be set needs enum<>label translation
    parity = resolve_generic(args, 'parity', Enum, serial.PARITY_NONE)
    # can't be set needs enum<>label translation
    stopbits = resolve_generic(args, 'stopbits', Enum, serial.STOPBITS_ONE)
    timeout = resolve_generic(args, 'timeout', float, 2.5)
    # maybe 0 or 1 works to set
    rtscts = resolve_generic(args, 'rtscts', bool, True) # on by default
    write_timeout = resolve_generic(args, 'write_timeout', float, 2.5)

    comms = MySerial(port = port,
        baudrate = baudrate,
        parity = parity,
        stopbits = stopbits,
        timeout = timeout,
        xonxoff = False,
        rtscts = rtscts,
        dsrdtr = True,
        write_timeout = write_timeout)


    if not comms.is_open:
        print(f"ERROR: Serial port {portname} could not be opened", file=sys.stderr)
        return None
    return comms


# Python boxed int type, LOL
class IntWrapper():
    def __init__(self, initial_value: int = 0):
        self._value = initial_value


    def increment(self) -> int:
        self._value += 1
        return self._value


    def set_zero(self) -> int:
        self._value = 0
        return self._value


    @property
    def value(self) -> int:
        return self._value


class MyVerboseAction(argparse.Action):
    def __init__(self, wrapper: IntWrapper, *args, **kwargs):
        super(MyVerboseAction, self).__init__(*args, **kwargs)
        assert callable(getattr(wrapper, "increment", None)) # duck typing
        self._wrapper = wrapper


    def __call__(self, parser, namespace, values, option_string) -> None:
        self._wrapper.increment()
        setattr(namespace, self.dest, self._wrapper.value)


    def format_usage(self) -> str:
        return super().format_usage()


class MyQuietAction(argparse.Action):
    def __init__(self, wrapper: IntWrapper, *args, **kwargs):
        super(MyQuietAction, self).__init__(*args, **kwargs)
        assert callable(getattr(wrapper, "set_zero", None)) # duck typing
        self._wrapper = wrapper


    def __call__(self, parser, namespace, values, option_string) -> None:
        self._wrapper.set_zero()
        setattr(namespace, self.dest, self._wrapper.value)


    def format_usage(self) -> str:
        return super().format_usage()


#############################################################################
if __name__ == '__main__':
    verbose_level = IntWrapper(1) # default verbose level
    parser = argparse.ArgumentParser(
                    prog='pyttloader',
                    description='TinyTapeout MicroPython load and runner',
                    epilog='https://github.com/dlmiles/tt04-muldiv4/tree/main/commander/pyttloader',
                    add_help=False)
    parser.add_argument('upload_file', nargs=1, metavar='uploadfile',
                        help='The MicroPython program to upload')
    parser.add_argument('sendexpect', nargs='*',
                        help='Send/Expect scripts NOIMPL')
    parser.add_argument('-R', '--machine-reset',
                        action=argparse.BooleanOptionalAction,
                        default=True,
                        help='Perform machine.reset()')
    parser.add_argument('--capture-write',
                        action=argparse.BooleanOptionalAction, default=False,
                        help='Capture Output Data [Off]')
    parser.add_argument('--capture-mode', metavar='int_value',
                        action='store', type=int, default=None, # default is managed in code
                        help='Capture Mode Mask 0-31 [1]')
    parser.add_argument('--capture',
                        action=argparse.BooleanOptionalAction,
                        default=True,
                        help='Capture Enable [On]')
    parser.add_argument('-C', '--capture-file', 
                        nargs='?', metavar='capturefile',
                        help='Capture file [capture.txt]',
                        default='capture.txt')
    parser.add_argument('-D', '--device',
                        action='store', nargs='?', dest='port',
                        default=None, # auto-detect
                        help='Serial device [auto-detect]')
    parser.add_argument('-q', '--quiet', nargs=0,
                        action=MyQuietAction, wrapper=verbose_level,
                        help="Set verbose level to 0")
    parser.add_argument('-?', '-h', '--help',
                        action='help',
                        help="Show help message")
    parser.add_argument('-v', '--verbose', nargs=0,
                        action=MyVerboseAction, wrapper=verbose_level,
                        help="Increase verbosity")
    parser.add_argument('-V', '--version', action='version', version='%(prog)s 0.1-beta')
    args = parser.parse_args()

    if verbose_level.value > 1:
        print(f"VERBOSE={verbose_level.value}")
        verbose = verbose_level.value
    
    # FIXME use this to setup logger, then reenable commented print out parts

    if getattr(args, 'help', False):
        parser.print_help()
        sys.exit(0)

    comms = serial_open(args)
    if not comms:
        sys.exit(1)

    if args.capture:
        comms.set_capture_file(args.capture_file, args.capture_write)

    if args.sendexpect and len(args.sendexpect) != 0:
        print(f"ERROR: 'sendexpect' feature is not yet implemented, please remove extra argument(s)", file=sys.stderr)
        sys.exit(1)

    if len(args.upload_file) != 1 or not os.path.isfile(args.upload_file[0]):
        print(f"ERROR: {args.upload_file[0]}: File does not exist", file=sys.stderr)
        sys.exit(1)

    # FIXME set this from -vvvvv if not explicitly from --capture-mode 31
    # although -vvv should be more about what ends up on stdout which is why --capture-mode exists as well

    if args.capture_mode is not None:
        capture_mode = args.capture_mode
    else:
        capture_mode = 0
        # 0x01 = data recv (default)
        capture_mode |= 0x01
        # 0x02 = data sent
        if args.capture_write == True or verbose_level.value > 4:
            capture_mode |= 0x02
        # 0x04 = upload recv
        #capture_mode |= 0x04
        # 0x08 = upload sent
        #capture_mode |= 0x08
        # 0x10 = upload control
        #capture_mode |= 0x10

    run_sequence(comms,
        upload_file=args.upload_file[0],
        capture_mode=capture_mode,
        machine_reset=args.machine_reset,
        )

    retval = 1 # error
    if comms.is_open:
        retval = 0 # no error
        comms.close()
        print(f"SUCCESS")
    else:
        print(f"FAILURE")
    sys.exit(retval)
