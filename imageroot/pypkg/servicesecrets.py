#
# Copyright (C) 2026 tebbi
# SPDX-License-Identifier: GPL-3.0-or-later
#

"""Per-container secret files for the ARSnova pod.

The same secret is expected under a different variable name by almost every
container (JWT secret, database passwords), so state/passwords.env cannot be
loaded as it is. render() writes one private env file per service under
state/secrets/, which the units pass to podman with --env-file. Nothing ends
up in state/environment or on a command line.
"""

import os

import modsecrets

# file name -> {variable expected by the container: key in passwords.env}
SERVICE_FILES = {
    "couchdb.env": {"COUCHDB_PASSWORD": "COUCHDB_PASSWORD"},
    "postgres-auth.env": {"POSTGRES_PASSWORD": "PG_AUTH_PASSWORD"},
    "postgres-comment.env": {"POSTGRES_PASSWORD": "PG_COMMENT_PASSWORD"},
    "authz.env": {"SPRING_DATASOURCE_PASSWORD": "PG_AUTH_PASSWORD", "SECURITY_JWT_SECRET": "JWT_SECRET"},
    "comments.env": {"SPRING_DATASOURCE_PASSWORD": "PG_COMMENT_PASSWORD", "SECURITY_JWT_SECRET": "JWT_SECRET"},
    "core.env": {"SYSTEM_COUCHDB_PASSWORD": "COUCHDB_PASSWORD", "SECURITY_JWT_SECRET": "JWT_SECRET"},
    "websocket.env": {"SECURITY_JWT_SECRET": "JWT_SECRET"},
    "gateway.env": {"SECURITY_JWT_PUBLIC_SECRET": "JWT_SECRET", "SECURITY_JWT_INTERNAL_SECRET": "JWT_SECRET"},
}


def render():
    state = os.environ.get("AGENT_STATE_DIR") or os.path.expanduser("~/.config/state")
    target = os.path.join(state, "secrets")
    secrets = modsecrets.read()
    old_umask = os.umask(0o077)
    try:
        os.makedirs(target, mode=0o700, exist_ok=True)
        for name, mapping in SERVICE_FILES.items():
            tmp = os.path.join(target, name + ".tmp")
            with open(tmp, "w") as fp:
                for variable, key in mapping.items():
                    fp.write(f"{variable}={secrets.get(key, '')}\n")
            os.replace(tmp, os.path.join(target, name))
    finally:
        os.umask(old_umask)
