@echo off

set PYTHON=
set GIT=
set VENV_DIR=
set COMMANDLINE_ARGS=--disable-nan-check --opt-sub-quad-attention %*

call webui.bat
