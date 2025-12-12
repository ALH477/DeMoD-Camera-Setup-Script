#!/bin/bash
SHARE_DIR="@share@"
MEDIAMTX_BIN="@mediamtx@"

cd "$SHARE_DIR"
"$MEDIAMTX_BIN" mediamtx.yml
