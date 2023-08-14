#!/bin/bash

set -e
mkdir -p /home/raghuram/Workspace/dmerk/TEST_DATA
cd /home/raghuram/Workspace/dmerk/TEST_DATA

########## Create Special Test Cases ##########
mkdir SPECIAL && cd SPECIAL

mkdir CHAR_DEVICE && cd CHAR_DEVICE
sudo -k mknod devzero c 1 5
cd ..

# symlink to a special file
mkdir SYMLINK_TO_SPECIAL && cd SYMLINK_TO_SPECIAL
ln -s ../CHAR_DEVICE/devzero symlink
cd ..

# broken symlink
mkdir SYMLINK_BROKEN && cd SYMLINK_BROKEN
ln -s non_existent_file symlink
cd ..

mkdir BLOCK_DEVICE && cd BLOCK_DEVICE
sudo -k mknod devloop100 b 7 100
cd ..

mkdir SOCKET && cd SOCKET
python3 -c "import socket as s; s.socket(s.AF_UNIX).bind('sock')"
cd ..

mkdir NAMEDPIPE && cd NAMEDPIPE
mkfifo namedpipe
cd ..
################################################
