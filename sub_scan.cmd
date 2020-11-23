@echo off
cls
:upload_loop
IF "%1"=="" GOTO completed
  python D:\sub_helper\sub_scan\sub_scan.py -u username -p password -f %1
  SHIFT
  GOTO upload_loop
:completed
pauses