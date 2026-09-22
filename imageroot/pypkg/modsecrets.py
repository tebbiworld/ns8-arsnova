#
# Copyright (C) 2026 tebbi
# SPDX-License-Identifier: GPL-3.0-or-later
#

"""Module secrets, kept out of the agent environment.

state/environment is mirrored by the NS8 agent to Redis in plain text, so
passwords, tokens and keys are stored in state/passwords.env (mode 0600)
instead. The file is listed in etc/state-include.conf, loaded by the systemd
units with EnvironmentFile= and read by the actions through this module.

Every change is a read-modify-write under an exclusive lock, like
agent.set_env() does for state/environment: two actions writing different
secrets at the same time must not lose each other's update.
"""

import contextlib
import fcntl
import os
import sys

import agent

FILENAME = "passwords.env"


def _state_dir():
    return os.environ.get("AGENT_STATE_DIR") or os.path.expanduser("~/.config/state")


def path():
    return os.path.join(_state_dir(), FILENAME)


@contextlib.contextmanager
def _locked():
    """Exclusive lock for a read-modify-write cycle of the secrets file."""
    lock_path = os.path.join(_state_dir(), "." + FILENAME + ".lock")
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def _read_unlocked():
    try:
        return agent.read_envfile(path())
    except FileNotFoundError:
        return {}


def _write_unlocked(values):
    old_umask = os.umask(0o077)
    try:
        agent.write_envfile(path(), values)
    finally:
        os.umask(old_umask)
    os.chmod(path(), 0o600)


def read():
    """Return the secrets as a dictionary (empty if the file does not exist)."""
    return _read_unlocked()


def get(key, default=""):
    return read().get(key, default)


def write(values):
    """Merge values into the secrets file, keeping it private (0600)."""
    with _locked():
        current = _read_unlocked()
        current.update({k: str(v) for k, v in values.items()})
        _write_unlocked(current)
    return current


def ensure(defaults):
    """Store the given values only for keys that have no value yet."""
    with _locked():
        current = _read_unlocked()
        missing = {k: str(v) for k, v in defaults.items() if not current.get(k)}
        if missing or not os.path.exists(path()):
            current.update(missing)
            _write_unlocked(current)
    return missing


def export_to_environ(*keys):
    """Put secrets into this process' environment, for tools that read a
    password from there (e.g. openssl "-passout env:NAME"). Values already
    present in the environment win."""
    current = read()
    for key in keys:
        if not os.environ.get(key) and current.get(key):
            os.environ[key] = current[key]


def migrate_from_env(keys, aliases=None):
    """Move legacy secrets from state/environment into the secrets file.

    aliases maps an extra name to an existing key, for containers that expect
    the same secret under another variable name.
    """
    env = agent.read_envfile(os.path.join(_state_dir(), "environment"))
    with _locked():
        current = _read_unlocked()
        changed = not os.path.exists(path())
        for key in keys:
            if env.get(key) and not current.get(key):
                current[key] = env[key]
                changed = True
        for alias, key in (aliases or {}).items():
            if current.get(key) and current.get(alias) != current.get(key):
                current[alias] = current[key]
                changed = True
        if changed:
            _write_unlocked(current)
    leftover = [k for k in keys if k in env]
    if leftover:
        agent.munset_env(leftover)
        print("moved out of state/environment: " + " ".join(leftover), file=sys.stderr)
    return leftover
