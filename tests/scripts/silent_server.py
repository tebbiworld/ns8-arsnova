#!/usr/bin/env python3
#
# Copyright (C) 2026 tebbi
# SPDX-License-Identifier: GPL-3.0-or-later
#

"""Test helper: a TCP server that accepts connections and never answers.

Stands in for an LDAP server (or the node's ldapproxy in front of an
unreachable domain controller) that takes the connection and then hangs.
Usage: silent_server.py PORT   (runs until it is killed)
"""

import socket
import sys


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: silent_server.py PORT")
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", int(sys.argv[1])))
    server.listen(16)
    clients = []  # keep the sockets open: the peer waits for an answer
    while True:
        clients.append(server.accept()[0])


if __name__ == "__main__":
    main()
