# Changelog

## 1.3.0 — unreleased

### Added

- **Directory login through a user domain of the cluster.** The settings offer
  a user domain of this cluster (recommended: no credentials stored in the
  module, the bind account is read through the node's ldapproxy at every start
  and followed on `user-domain-changed`) or, as before, an LDAP server of its
  own. Same settings and settings page component as ns8-clamav and
  ns8-idevice-backup (`pypkg/ldapsettings.py`, `LdapLogin.vue`); the module
  declares `cluster:accountconsumer`. The group is picked from a list for a
  user domain; nested Active Directory groups count, disabled accounts cannot
  log in.

### Changed

- **The bind password no longer leaves the module.** `get-configuration`
  returns `ldap_bind_password_set` instead of the password; an empty password
  field keeps the stored one.
- **Certificate check for an LDAP server of its own.** With the check on, the
  core verifies the certificate against the public CAs and checks the host
  name (no more `disableEndpointIdentification`). With the check off, the
  certificate the server presents is trusted when the core starts. A server on
  the same node keeps its host name (`--add-host … :host-gateway`) instead of
  being replaced by `host.containers.internal`.
- Existing manual LDAP settings are migrated on update unchanged in behaviour:
  source "LDAP server of its own", certificate check off, and the user filter
  of 1.2.0 (direct group membership, no object class, so OpenLDAP servers keep
  working) until the directory settings are changed and saved. Settings that
  1.2.0 did not apply (no URL or base DN) are switched off.
- `list-ldap-groups` lists the groups of a user domain (input `domain`).
- **CouchDB 3.2 → 3.5** (`particify/couchdb:3.5`, CouchDB 3.5.2, the version
  of Particify's own 3.13 compose file). CouchDB 3.2 was built on Debian 11,
  which no longer receives security updates. CouchDB upgrades the database
  files in place when it starts; there is no way back to 3.2 other than
  restoring a backup made before the update.
- **RabbitMQ 3.11 → 4.3** (`particify/rabbitmq-stomp:4.3-alpine`, RabbitMQ
  4.3.1, as in Particify's 3.13 compose file). RabbitMQ 4 cannot start on the
  data of 3.11 (feature flags; the supported path passes every minor release).
  The broker holds no data that must survive: the services declare their
  queues at every start and the messages are short-lived events. On update,
  `update-module.d/10reset_rabbitmq` therefore starts the broker on an empty
  volume whenever its image changes. Events in flight during the update are
  lost (the services are restarted at the same time anyway).

### Fixed

- `list-ldap-groups` failed when no password was typed in (missing import).

## 1.2.0 — 2026-09-19

Alignment with the NethServer module conventions (NethServer/agents skills).

### Changed

- **Secrets moved out of the module environment.** The JWT secret, the CouchDB and PostgreSQL passwords and the LDAP bind password are now kept in `state/passwords.env` (mode 0600) instead of `state/environment`, which NS8 mirrors to Redis in plain text. Each container gets its secrets from a private env file under `state/secrets/`, so they no longer appear on the podman command line. Existing installations are migrated on update; the values do not change.
- **Module backup now contains the data.** New `etc/state-include.conf`: the backup holds `pg_dump` files of both PostgreSQL databases (written by `module-dump-state`), the CouchDB volume and the secrets file. Before, only the module environment was saved.
- **Working restore.** New `restore-module` steps rebuild both databases from the dumps and re-apply every setting, including the directory login.
- **Fully pinned images.** Dated `3.13.20260613` builds for the ARSnova services; digests for the proxy, CouchDB and RabbitMQ images, which only have rolling tags. The auto-release follows the dated tags.

### Added

- Robot Framework tests (install, update from the previous release, backup and restore) run on real NS8 nodes through `stephdl/ns8-ci-actions`.

### Platform integration

- **Clone and move.** New `clone-module` step (a link to the restore step): a cloned or moved instance gets its route and settings back instead of coming up unconfigured. The settings are read from the source instance, including those a new instance starts with a default for.
- Release notes are linked from the software centre (`relnotes_url`).

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
