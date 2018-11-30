#!/bin/bash

curdir=$(pwd)
[[ -d $1 ]] && curdir=$1

export DOCSERV_SHARE_DIR=$curdir/share
export DOCSERV_BIN_DIR=$curdir/bin
export DOCSERV_CONFIG_DIR=$curdir/config

export PATH="${DOCSERV_BIN_DIR}:"$(printenv PATH)
export PS1="ds²-dev "$(printenv PS1)
