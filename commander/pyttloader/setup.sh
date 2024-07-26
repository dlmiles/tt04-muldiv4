#!/usr/bin/env bash
#
#
set -e

basedir=$(dirname "$0")


# Some platforms have multiple pythons available and the
#  default is not the latest.
if test -z "$PYTHON"
then
	if which python3.11 >/dev/null 2>/dev/null
	then
		PYTHON=python3.11
	elif which python3.10 >/dev/null 2>/dev/null
	then
		PYTHON=python3.10
	elif which python3.10 >/dev/null 2>/dev/null
	then
		PYTHON=python3.10
	elif which python3 >/dev/null 2>/dev/null
	then
		PYTHON=python3
	else
		PYTHON=python
	fi
fi

echo "PYTHON=$PYTHON"

"$PYTHON" -m venv "${basedir}/venv"

source "${basedir}/venv/bin/activate"

venv/bin/pip install -r "${basedir}/requirements.txt"

echo ""
echo "############################################################"
echo "### SUCCESS: Environment venv setup"
echo "### Type the following commands to use pyttloader.py repl.py"
echo "source ${basedir}/venv/bin/activate"
echo "${basedir}/pyttloader.py -D /dev/ttyACM0 --capture --machine-reset repl.py"
echo "### or"
echo "${basedir}/pyttloader.py --machine-reset repl.py"
echo "############################################################"
echo ""
