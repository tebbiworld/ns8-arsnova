# Changelog

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

- **Clone and move.** New `clone-module` step (a link to the restore step): a cloned or moved instance gets its route and settings back instead of coming up unconfigured.
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
