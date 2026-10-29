#
# Copyright (C) 2026 tebbi
# SPDX-License-Identifier: GPL-3.0-or-later
#

"""ARSnova side of the shared directory login (pypkg/ldapsettings.py).

ldapsettings.py stores the settings exactly as in ns8-clamav and
ns8-idevice-backup (user domain of the cluster or an LDAP server of its own).
Those modules check the password in their own Python code; ARSnova's backend
core does it with Spring Security LDAP, configured by environment variables.
This module turns the stored settings into that configuration:

  ldap.env         SECURITY_AUTHENTICATIONPROVIDERS_LDAP_0_* (+ JAVA_TOOL_OPTIONS),
                   --env-file of the core container, carries the bind password:
                   mode 0600, written before every start, not in the backup
  ldap-podman.env  LDAP_PODMAN_ARGS, extra podman options of the core container
  ad-truststore.p12  only for a server of its own with the certificate check
                   off: the JDK CAs plus the certificate the server presents

How the core reaches the directory:
  user domain   through the node's ldapproxy, which listens on the node
                loopback. Containers of a rootless bridge network cannot reach
                the node loopback, so the module user's pasta maps it to
                LOOPBACK_ALIAS (~/.config/containers/containers.conf, written
                only while a user domain is in use). Clear LDAP on the
                loopback; the proxy talks TLS to the domain controllers.
  own server    directly. A host name that resolves to this node gets an
                --add-host entry to the node (host-gateway), so the name and
                with it the certificate check stay intact.

Spring Security only knows a user search filter, so group membership is part
of that filter: memberOf with LDAP_MATCHING_RULE_IN_CHAIN on Active Directory
(nested groups count). OpenLDAP (rfc2307) groups list memberUid values, which a
user filter cannot test: a group restriction is refused there.
"""

import ipaddress
import json
import os
import socket
import ssl
import subprocess
import sys
import urllib.parse

import agent
import ldapsettings

# address under which the containers reach the node loopback (pasta
# --map-host-loopback); podman itself uses 169.254.1.1 (DNS) and
# 169.254.1.2 (host.containers.internal)
LOOPBACK_ALIAS = "169.254.1.3"
CONTAINERS_CONF = os.path.expanduser("~/.config/containers/containers.conf")
CONTAINERS_CONF_HEADER = "# Written by the ARSnova module (pypkg/arsnovaldap.py). Do not edit by hand.\n"
LDAP_ENV = "ldap.env"
PODMAN_ENV = "ldap-podman.env"
GROUP_CACHE = "ldap-group.cache"
TRUSTSTORE = "/etc/ssl/ad-truststore.p12"  # path inside the core container
PREFIX = "SECURITY_AUTHENTICATIONPROVIDERS_LDAP_0_"
TIMEOUT = 10
# keys of the module environment that 1.3.0 no longer uses
OBSOLETE_KEYS = ("LDAP_HOST", "LDAP_PORT")
LDAP_FIELDS = ("ldap_domain", "ldap_group", "ldap_url", "ldap_base_dn", "ldap_bind_dn",
               "ldap_bind_password", "ldap_user_attribute", "ldap_title")


def _log(msg, level=agent.SD_WARNING):
    print(level + msg, file=sys.stderr)


def enabled(env=None):
    """LDAP_ENABLED: "true" since 1.3.0, "True" before (Python bool)."""
    env = os.environ if env is None else env
    return (env.get("LDAP_ENABLED") or "").lower() == "true"


# --- migration -----------------------------------------------------------------

def legacy_updates(env):
    """Environment changes for settings written before 1.3.0, when only a
    server entered by hand existed: keep exactly that behaviour (source
    custom, Active Directory filter, certificate pinned at start without a
    host name check). Returns {} when nothing is to change."""
    if env.get("LDAP_SOURCE"):
        return {}
    url = (env.get("LDAP_URL") or "").strip()
    updates = {
        "LDAP_SOURCE": "custom" if url else "domain",
        "LDAP_ENABLED": "true" if enabled(env) else "false",
    }
    if url:
        updates.update({
            "LDAP_TLS_VERIFY": "false",
            "LDAP_START_TLS": "false",
            "LDAP_SCHEMA": "ad",
            "LDAP_USER_ATTRIBUTE": env.get("LDAP_USER_ATTRIBUTE") or "sAMAccountName",
        })
    return updates


# --- validation ----------------------------------------------------------------

def _source(data):
    return data.get("ldap_source") or os.environ.get("LDAP_SOURCE") or ("custom" if data.get("ldap_url") else "domain")


def _domain_schema(domain):
    import cluster.userdomains
    try:
        domains = cluster.userdomains.list_domains(agent.redis_connect(use_replica=True))
    except Exception:
        return ""
    return (domains.get(domain) or {}).get("schema", "")


def validate(data, active):
    """ARSnova limits on top of ldapsettings.validate(): list of (field, error)."""
    errors = []
    # the values end up in env files and Spring properties: a line break would
    # add a variable, "${" would be read as a property placeholder
    for field in LDAP_FIELDS:
        value = data.get(field)
        if isinstance(value, str) and (any(ord(c) < 32 for c in value) or "${" in value):
            errors.append((field, "ldap_value_invalid"))
    if not active:
        return errors
    source = _source(data)
    group = (data.get("ldap_group") or "").strip()
    if "{" in group or "}" in group:
        errors.append(("ldap_group", "ldap_value_invalid"))
    attribute = (data.get("ldap_user_attribute") or "").strip()
    if source == "custom" and attribute and not _is_attribute_name(attribute):
        errors.append(("ldap_user_attribute", "ldap_value_invalid"))
    if source == "custom" and data.get("ldap_start_tls"):
        # Spring Security LDAP in ARSnova has no StartTLS setting
        errors.append(("ldap_start_tls", "start_tls_unsupported"))
    if group:
        if source == "custom":
            schema = data.get("ldap_schema") or "ad"
        else:
            schema = _domain_schema((data.get("ldap_domain") or "").strip())
        if schema == "rfc2307":
            errors.append(("ldap_group", "group_needs_ad"))
    return errors


def _is_attribute_name(name):
    return name[0].isalpha() and all(c.isalnum() or c == "-" for c in name)


# --- node loopback for the user domain ---------------------------------------------

def needs_host_loopback():
    """The core must reach the node loopback: ldapproxy of a user domain."""
    return enabled() and os.environ.get("LDAP_SOURCE", "domain") == "domain"


def configure_host_loopback():
    """Write or remove the pasta loopback mapping of the module user. Return
    True when it changed: the rootless network is then recreated only after
    every container of the module stopped (see configure-module/80start_services)."""
    wanted = None
    if needs_host_loopback():
        wanted = CONTAINERS_CONF_HEADER + (
            "# The ARSnova core reaches the node's ldapproxy (user domain login) at\n"
            f"# {LOOPBACK_ALIAS}; see the module README.\n"
            "[network]\n"
            f'pasta_options = ["--map-host-loopback", "{LOOPBACK_ALIAS}"]\n')
    try:
        with open(CONTAINERS_CONF) as fp:
            current = fp.read()
    except FileNotFoundError:
        current = None
    if current == wanted:
        return False
    if wanted is None:
        if not current.startswith(CONTAINERS_CONF_HEADER):
            return False  # not ours: leave it alone
        os.unlink(CONTAINERS_CONF)
    else:
        os.makedirs(os.path.dirname(CONTAINERS_CONF), exist_ok=True)
        with open(CONTAINERS_CONF + ".tmp", "w") as fp:
            fp.write(wanted)
        os.replace(CONTAINERS_CONF + ".tmp", CONTAINERS_CONF)
    return True


def host_loopback_active():
    """The running rootless network maps the node loopback (pasta option)."""
    try:
        out = subprocess.run(["pgrep", "-u", str(os.getuid()), "-a", "pasta"],
                             capture_output=True, text=True).stdout
    except OSError:
        return False
    return any("rootless-netns" in line and f"--map-host-loopback {LOOPBACK_ALIAS}" in line
               for line in out.splitlines())


# --- addresses -------------------------------------------------------------------

def _node_addresses():
    addrs = set()
    try:
        out = subprocess.run(["/usr/sbin/ip", "-j", "addr"], capture_output=True, text=True, check=True).stdout
        for link in json.loads(out):
            for a in link.get("addr_info", []):
                addrs.add(a.get("local", ""))
    except (OSError, subprocess.CalledProcessError, ValueError):
        pass
    return addrs


def _resolve(host):
    try:
        return {ai[4][0] for ai in socket.getaddrinfo(host, None)}
    except socket.gaierror:
        return set()


def _container_address(host):
    """(host the container connects to, extra podman options) for a server
    of its own. Rootless containers cannot connect to the node's own address:
    a host name of this node is mapped to the node with --add-host (the name
    and the certificate check stay), an IP address is replaced."""
    targets = _resolve(host)
    if not targets & _node_addresses():
        return host, ""
    try:
        ipaddress.ip_address(host)
        return "host.containers.internal", ""
    except ValueError:
        return host, f"--add-host={host}:host-gateway"


# --- group -----------------------------------------------------------------------

def _connection(v):
    import ldap3
    tls = None
    if v["LDAP_TLS"] == "ssl":
        verify = v.get("LDAP_TLS_VERIFY", "true") != "false"
        tls = ldap3.Tls(validate=ssl.CERT_REQUIRED if verify else ssl.CERT_NONE)
    server = ldap3.Server(v["LDAP_HOST"], port=int(v["LDAP_PORT"]), use_ssl=v["LDAP_TLS"] == "ssl",
                          tls=tls, connect_timeout=TIMEOUT)
    return ldap3.Connection(server, v["LDAP_BIND_DN"], v["LDAP_BIND_PASSWORD"],
                            auto_bind=True, receive_timeout=TIMEOUT)


def _lookup_group_dn(v, group):
    """DN of a group given by name (same search as ldapauth.py of the pilots)."""
    from ldap3.utils.conv import escape_filter_chars
    name = escape_filter_chars(group)
    if v["LDAP_SCHEMA"] == "ad":
        gfilter = f"(&(objectClass=group)(sAMAccountName={name}))"
    else:
        gfilter = f"(&(objectClass=posixGroup)(cn={name}))"
    with _connection(v) as conn:
        conn.search(v["LDAP_BASE_DN"], gfilter, attributes=[])
        entries = [e for e in conn.response if e.get("type") == "searchResEntry"]
    if len(entries) != 1:
        raise LookupError(f"group {group!r} not found ({len(entries)} matches)")
    return entries[0]["dn"]


def _group_dn(v, group):
    """Resolve the group; the last result is cached so a directory that is
    down while the core starts does not switch the restriction off."""
    if "=" in group:
        return group
    key = "|".join([v["LDAP_SOURCE"], v.get("LDAP_HOST", ""), v["LDAP_BASE_DN"], group])
    try:
        dn = _lookup_group_dn(v, group)
    except Exception as exc:
        try:
            with open(GROUP_CACHE) as fp:
                cached = json.load(fp)
        except (OSError, ValueError):
            cached = {}
        if cached.get("key") == key and cached.get("dn"):
            _log(f"cannot look up the group {group}: {exc}; using the last known DN")
            return cached["dn"]
        raise
    with open(GROUP_CACHE + ".tmp", "w") as fp:
        json.dump({"key": key, "dn": dn}, fp)
    os.replace(GROUP_CACHE + ".tmp", GROUP_CACHE)
    return dn


# --- core configuration --------------------------------------------------------------

def render():
    """(ldap.env lines, LDAP_PODMAN_ARGS, truststore host/port or None).

    Every problem leaves the LDAP provider off (fail secure): local and
    registered accounts keep working, directory logins are refused.
    """
    off = (["# directory login off"], "", None)
    if not enabled():
        return off
    v = dict(line.split("=", 1) for line in ldapsettings.env_lines(True))
    if not v.get("LDAP_HOST"):
        return off  # user domain not available, ldapsettings logged why
    source, schema = v["LDAP_SOURCE"], v.get("LDAP_SCHEMA", "ad")
    attribute = v.get("LDAP_USER_ATTRIBUTE") or ("sAMAccountName" if schema == "ad" else "uid")
    podman_args, truststore = "", None
    java_options = ""
    extra = ""
    if source == "domain":
        if not host_loopback_active():
            _log("the rootless network does not map the node loopback yet: save the settings again "
                 "(configure-module restarts the whole module)")
            return off
        host, scheme = LOOPBACK_ALIAS, "ldap"
        try:
            from agent.ldapproxy import Ldapproxy
            # hide the accounts NS8 hides (krbtgt, ldapservice, ...)
            extra = Ldapproxy().get_ldap_users_search_filter_clause(os.environ.get("LDAP_DOMAIN", ""))
        except Exception as exc:
            _log(f"cannot read the hidden users of the domain: {exc}")
    else:
        if v["LDAP_TLS"] == "starttls":
            _log("StartTLS is not supported by ARSnova: use an ldaps:// URL")
            return off
        host, podman_args = _container_address(v["LDAP_HOST"])
        scheme = "ldaps" if v["LDAP_TLS"] == "ssl" else "ldap"
        if v["LDAP_TLS"] == "ssl" and v.get("LDAP_TLS_VERIFY") == "false":
            # trust the certificate the server presents, without a host name
            # check (the behaviour of every version before 1.3.0)
            truststore = (v["LDAP_HOST"], v["LDAP_PORT"])
            java_options = (f"-Djavax.net.ssl.trustStore={TRUSTSTORE} -Djavax.net.ssl.trustStorePassword=changeit"
                            " -Djavax.net.ssl.trustStoreType=PKCS12"
                            " -Dcom.sun.jndi.ldap.object.disableEndpointIdentification=true")

    group_filter = ""
    group = v.get("LDAP_GROUP", "")
    if group:
        if schema != "ad":
            _log(f"group {group}: a group restriction needs Active Directory, directory login stays off")
            return off
        try:
            dn = _group_dn(v, group)
        except Exception as exc:
            _log(f"cannot look up the group {group}: {exc}; directory login stays off")
            return off
        from ldap3.utils.conv import escape_filter_chars
        group_filter = f"(memberOf:1.2.840.113556.1.4.1941:={escape_filter_chars(dn)})"
    if schema == "ad":
        user_filter = (f"(&(objectClass=user)({attribute}={{0}})"
                       f"(!(userAccountControl:1.2.840.113556.1.4.803:=2)){extra}{group_filter})")
    else:
        user_filter = f"(&(objectClass=posixAccount)({attribute}={{0}}){extra})"

    base = urllib.parse.quote(v["LDAP_BASE_DN"], safe="=,")
    lines = [
        f"{PREFIX}ENABLED=true",
        f"{PREFIX}TITLE={os.environ.get('LDAP_TITLE') or 'LDAP'}",
        f"{PREFIX}HOSTURL={scheme}://{host}:{v['LDAP_PORT']}/{base}",
        # search-based authentication: find the user, then bind as the user
        f"{PREFIX}USERDNPATTERN=",
        f"{PREFIX}USERIDATTRIBUTE={attribute}",
        f"{PREFIX}USERSEARCHBASE=",
        f"{PREFIX}USERSEARCHFILTER={user_filter}",
        f"{PREFIX}MANAGERUSERDN={v['LDAP_BIND_DN']}",
        f"{PREFIX}MANAGERPASSWORD={v['LDAP_BIND_PASSWORD']}",
        f"{PREFIX}ALLOWEDROLES_0=MODERATOR",
        f"{PREFIX}ALLOWEDROLES_1=PARTICIPANT",
    ]
    if java_options:
        lines.append(f"JAVA_TOOL_OPTIONS={java_options}")
    for line in lines:
        value = line.split("=", 1)[1]
        if "\n" in value or "\r" in value or "${" in value:
            _log(f"{line.split('=', 1)[0]}: value not usable in the core configuration, directory login stays off")
            return off
    return lines, podman_args, truststore


def _write_private(path, text):
    old_umask = os.umask(0o077)
    try:
        with open(path + ".tmp", "w") as fp:
            fp.write(text)
        os.replace(path + ".tmp", path)
    finally:
        os.umask(old_umask)


def discover():
    """ExecStartPre of arsnova-core (bin/discover-ldap)."""
    lines, podman_args, truststore = render()
    header = "# Generated by bin/discover-ldap before every start. Do not edit by hand."
    _write_private(LDAP_ENV, "\n".join([header] + lines) + "\n")
    _write_private(PODMAN_ENV, f"{header}\nLDAP_PODMAN_ARGS={podman_args}\n")
    if truststore:
        env = dict(os.environ, LDAP_HOST=truststore[0], LDAP_PORT=str(truststore[1]))
        result = subprocess.run(["build-ldap-truststore"], env=env)
        if result.returncode != 0:
            _log("build-ldap-truststore failed: LDAPS logins may fail")
    described = "off" if lines == ["# directory login off"] else f"{os.environ.get('LDAP_SOURCE')} {lines[2].split('=', 1)[1]}"
    _log(f"directory login: {described}", agent.SD_INFO)
