# Changelog

## 1.1.1 — 2026-09-12

### Fixed

- **AD/LDAP login failed when the directory server runs on the same node.**
  With the rootless default network the node's own IP address is mirrored into
  the container, so a connection to it is refused instead of reaching the host.
  When the configured LDAP host resolves to this node, the core now connects
  through `host.containers.internal` (new helper `bin/ldap-container-host`);
  other hosts are unaffected. The LDAPS truststore is still built from the real
  host name.
- `update-module` re-runs that detection and restarts the services, so the fix
  applies to existing instances right after the update.

## 1.1.0

- Self-registration toggle; category fix; license/trademark notes.
