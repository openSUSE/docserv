#!/bin/bash

curdir=$(pwd)
[[ -d $1 ]] && curdir=$1

export DOCSERV_SHARE_DIR=$curdir/share
export DOCSERV_BIN_DIR=$curdir/bin
export DOCSERV_CONFIG_DIR=$curdir/config
export DOCSERV_CACHE_DIR=$curdir/cache

[[ -e $DOCSERV_CACHE_DIR ]] || mkdir -p $DOCSERV_CACHE_DIR

export PATH="${DOCSERV_BIN_DIR}:"$(printenv PATH)
export PS1="ds²-dev "$(printenv PS1)

if [[ "$DO_NOT_PRINT_PATHS" -ne 1 ]]; then
  echo "Variables set:"
  echo "  DOCSERV_SHARE_DIR  $DOCSERV_SHARE_DIR"
  echo "  DOCSERV_BIN_DIR    $DOCSERV_BIN_DIR"
  echo "  DOCSERV_CONFIG_DIR $DOCSERV_CONFIG_DIR"
  echo "  DOCSERV_CACHE_DIR  $DOCSERV_CACHE_DIR"
fi
