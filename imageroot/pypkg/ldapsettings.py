#
# Copyright (C) 2026 tebbi
# SPDX-License-Identifier: GPL-3.0-or-later
#

"""Directory login settings shared by the tebbiworld NS8 modules (kept
identical in ns8-clamav and ns8-idevice-backup, imageroot/pypkg).

The login source is either
  domain  a user domain of this cluster: nothing but its name is stored, the
          connection (ldapproxy on the node loopback, bind account) is read
          when the service starts, so password changes and DC moves follow
          automatically (label cluster:accountconsumer, event
          user-domain-changed), or
  custom  an LDAP server of its own: URL, bind DN, base DN, schema, login
          attribute and TLS check in the module environment, the bind
          password in state/passwords.env (never in the environment, which
          the agent mirrors to Redis in plain text).

Input/output names (configure-module, get-configuration):
  ldap_source, ldap_domain, ldap_group, ldap_url, ldap_start_tls,
  ldap_tls_verify, ldap_schema, ldap_base_dn, ldap_bind_dn,
  ldap_bind_password (write only), ldap_user_attribute
"""

import os
import sys
import urllib.parse

import agent
import modsecrets

SOURCES = ("domain", "custom")
PASSWORD_KEY = "LDAP_BIND_PASSWORD"


def _env(name, default=""):
    return os.environ.get(name, default)


def _set(name, value):
    agent.set_env(name, value)
    os.environ[name] = value


def apply(data, active, legacy_source="domain"):
    """Persist the settings of a configure-module request.

    active: the module uses a directory login at all (otherwise no user
    domain is bound). legacy_source: the source assumed when the request has
    no ldap_source (clients of an earlier version).
    """
    source = data.get("ldap_source") or _env("LDAP_SOURCE") or legacy_source
    if source not in SOURCES:
        agent.set_status("validation-failed")
        print(f"ldap_source must be one of {SOURCES}", file=sys.stderr)
        sys.exit(2)
    _set("LDAP_SOURCE", source)
    _set("LDAP_GROUP", (data.get("ldap_group") or "").strip())

    # for a server of its own LDAP_DOMAIN keeps its last value: some modules
    # use it as a label of the accounts (e.g. the owner domain of a device)
    if source == "domain":
        domain = (data.get("ldap_domain") or "").strip()
        _set("LDAP_DOMAIN", domain)
        # a user domain needs no credentials of the module: drop a bind
        # password stored for a server of its own
        if modsecrets.get(PASSWORD_KEY):
            modsecrets.write({PASSWORD_KEY: ""})

    if source == "custom":
        url = (data.get("ldap_url") or "").strip()
        _set("LDAP_URL", url)
        # a client that does not send a field keeps the stored value
        if "ldap_start_tls" in data:
            _set("LDAP_START_TLS", "true" if data["ldap_start_tls"] else "false")
        if "ldap_tls_verify" in data:
            _set("LDAP_TLS_VERIFY", "false" if data["ldap_tls_verify"] is False else "true")
        _set("LDAP_SCHEMA", data.get("ldap_schema") or _env("LDAP_SCHEMA") or "ad")
        _set("LDAP_BASE_DN", (data.get("ldap_base_dn") or "").strip())
        _set("LDAP_BIND_DN", (data.get("ldap_bind_dn") or "").strip())
        _set("LDAP_USER_ATTRIBUTE", (data.get("ldap_user_attribute") or "").strip())
        password = data.get("ldap_bind_password") or ""
        if password:
            modsecrets.write({PASSWORD_KEY: password})

    bind_domain(active)
    return source


def bind_domain(active):
    """Declare the user domain the module consumes (none for a server of its
    own or when the directory login is off)."""
    domain = _env("LDAP_DOMAIN") if _env("LDAP_SOURCE", "domain") == "domain" else ""
    bind = [domain] if active and domain else []
    if bind:
        import cluster.userdomains
        if domain not in cluster.userdomains.list_domains(agent.redis_connect(use_replica=True)):
            print(agent.SD_WARNING + f"user domain {domain} does not exist in this cluster: logins are refused", file=sys.stderr)
            bind = []
    agent.bind_user_domains(bind, check=True)


def complete():
    """The stored settings are enough to try a login."""
    if _env("LDAP_SOURCE", "domain") == "domain":
        return bool(_env("LDAP_DOMAIN"))
    return bool(_env("LDAP_URL") and _env("LDAP_BASE_DN") and _env("LDAP_BIND_DN") and modsecrets.get(PASSWORD_KEY))


def validate(data, active):
    """Return a list of (field, error) for a configure-module request."""
    errors = []
    if not active:
        return errors
    source = data.get("ldap_source") or _env("LDAP_SOURCE") or "domain"
    if source == "domain":
        domain = (data.get("ldap_domain") or "").strip()
        if not domain:
            errors.append(("ldap_domain", "ldap_domain_required"))
        else:
            import cluster.userdomains
            # a restore on a cluster without that domain keeps the stored
            # value: logins are then refused until it is fixed
            if domain not in cluster.userdomains.list_domains(agent.redis_connect(use_replica=True)) and domain != _env("LDAP_DOMAIN"):
                errors.append(("ldap_domain", "ldap_domain_unknown"))
    elif source == "custom":
        url = (data.get("ldap_url") or "").strip()
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("ldap", "ldaps") or not parsed.hostname:
            errors.append(("ldap_url", "ldap_url_invalid"))
        if parsed.scheme == "ldaps" and data.get("ldap_start_tls"):
            errors.append(("ldap_start_tls", "start_tls_with_ldaps"))
        for field in ("ldap_base_dn", "ldap_bind_dn"):
            if not (data.get(field) or "").strip():
                errors.append((field, field + "_required"))
        if not data.get("ldap_bind_password") and not modsecrets.get(PASSWORD_KEY):
            errors.append(("ldap_bind_password", "ldap_bind_password_required"))
    return errors


def configuration():
    """Settings for get-configuration; the bind password is never returned."""
    import cluster.userdomains
    try:
        domains = sorted(cluster.userdomains.list_domains(agent.redis_connect(use_replica=True)))
    except Exception as exc:
        print(agent.SD_WARNING + f"cannot list the user domains: {exc}", file=sys.stderr)
        domains = []
    return {
        "ldap_source": _env("LDAP_SOURCE", "domain"),
        "ldap_domain": _env("LDAP_DOMAIN"),
        "ldap_group": _env("LDAP_GROUP"),
        "ldap_url": _env("LDAP_URL"),
        "ldap_start_tls": _env("LDAP_START_TLS") == "true",
        "ldap_tls_verify": _env("LDAP_TLS_VERIFY", "true") != "false",
        "ldap_schema": _env("LDAP_SCHEMA", "ad") or "ad",
        "ldap_base_dn": _env("LDAP_BASE_DN"),
        "ldap_bind_dn": _env("LDAP_BIND_DN"),
        "ldap_user_attribute": _env("LDAP_USER_ATTRIBUTE"),
        "ldap_bind_password_set": bool(modsecrets.get(PASSWORD_KEY)),
        "user_domains": domains,
    }


def restore_data(default_source="domain"):
    """The ldap_* fields of configure-module from the restored environment
    (restore-module, clone-module); the bind password stays blank = keep the
    restored state/passwords.env."""
    return {
        "ldap_source": _env("LDAP_SOURCE") or default_source,
        "ldap_domain": _env("LDAP_DOMAIN"),
        "ldap_group": _env("LDAP_GROUP"),
        "ldap_url": _env("LDAP_URL"),
        "ldap_start_tls": _env("LDAP_START_TLS") == "true",
        "ldap_tls_verify": _env("LDAP_TLS_VERIFY", "true") != "false",
        "ldap_schema": _env("LDAP_SCHEMA", "ad") or "ad",
        "ldap_base_dn": _env("LDAP_BASE_DN"),
        "ldap_bind_dn": _env("LDAP_BIND_DN"),
        "ldap_user_attribute": _env("LDAP_USER_ATTRIBUTE"),
        "ldap_bind_password": "",
    }


def env_lines(active):
    """LDAP_* lines for the container (see ldapauth.py); carries the bind
    password, so the caller writes them to a 0600 file outside the backup."""
    lines = []
    if not active:
        return lines
    source = _env("LDAP_SOURCE", "domain")
    group = _env("LDAP_GROUP")
    if source == "domain":
        domain = _env("LDAP_DOMAIN")
        odom = None
        if domain:
            try:
                from agent.ldapproxy import Ldapproxy
                odom = Ldapproxy().get_domain(domain)
            except Exception as exc:
                print(agent.SD_WARNING + f"cannot read the user domain {domain}: {exc}", file=sys.stderr)
        if not odom:
            # the service still starts and refuses every login
            print(agent.SD_WARNING + f"user domain {domain or '(none)'} not available: logins are refused", file=sys.stderr)
            return ["LDAP_SOURCE=domain"]
        lines += [
            "LDAP_SOURCE=domain",
            f"LDAP_HOST={odom['host']}",
            f"LDAP_PORT={odom['port']}",
            "LDAP_TLS=none",  # the proxy listens on the node loopback
            f"LDAP_SCHEMA={odom['schema']}",
            f"LDAP_BASE_DN={odom['base_dn']}",
            f"LDAP_BIND_DN={odom['bind_dn']}",
            f"LDAP_BIND_PASSWORD={odom['bind_password']}",
        ]
    else:
        url = urllib.parse.urlparse(_env("LDAP_URL"))
        tls = "ssl" if url.scheme == "ldaps" else ("starttls" if _env("LDAP_START_TLS") == "true" else "none")
        lines += [
            "LDAP_SOURCE=custom",
            f"LDAP_HOST={url.hostname or ''}",
            f"LDAP_PORT={url.port or (636 if tls == 'ssl' else 389)}",
            f"LDAP_TLS={tls}",
            f"LDAP_TLS_VERIFY={_env('LDAP_TLS_VERIFY', 'true')}",
            f"LDAP_SCHEMA={_env('LDAP_SCHEMA', 'ad')}",
            f"LDAP_BASE_DN={_env('LDAP_BASE_DN')}",
            f"LDAP_BIND_DN={_env('LDAP_BIND_DN')}",
            f"LDAP_BIND_PASSWORD={modsecrets.get(PASSWORD_KEY) or ''}",
            f"LDAP_USER_ATTRIBUTE={_env('LDAP_USER_ATTRIBUTE')}",
        ]
    lines.append(f"LDAP_GROUP={group}")
    return lines


def write_env_file(path, active, header="# Generated by bin/discover-ldap. Do not edit by hand."):
    old_umask = os.umask(0o077)
    try:
        with open(path + ".tmp", "w") as fp:
            fp.write("\n".join([header] + env_lines(active)) + "\n")
        os.replace(path + ".tmp", path)
    finally:
        os.umask(old_umask)


def list_groups(domain):
    """Group names of a cluster user domain, for the group selection."""
    from agent.ldapclient import Ldapclient
    from agent.ldapproxy import Ldapproxy
    odom = Ldapproxy().get_domain(domain)
    if not odom:
        return []
    groups = Ldapclient.factory(**odom).list_groups()
    return sorted(({"name": g["group"], "description": g.get("description") or ""} for g in groups),
                  key=lambda g: g["name"].lower())
