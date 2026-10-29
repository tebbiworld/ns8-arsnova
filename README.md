# ns8-arsnova

A [NethServer 8](https://github.com/NethServer/ns8-core) module that packages
[ARSnova / Particify](https://github.com/particify/arsnova) — a live audience
response and interactive learning system (polls, quizzes, Q&A, live feedback).

ARSnova is a microservice stack. Because several services listen on port 8080
and find each other by DNS name, the module does **not** use a single pod:
instead it creates a dedicated rootless Podman network (`arsnova`) with built-in
DNS, and each service runs as its own container joined to that network. Only the
front reverse proxy is published to the host.

Containers (all official `particify/*` images, plus PostgreSQL):

- **arsnova-proxy** — nginx front proxy, the single published entry point
- **arsnova-web** — Angular web client
- **arsnova-http-gateway** — API gateway, fans `/api` out to the services
- **arsnova-ws-gateway** — WebSocket/STOMP gateway for live updates
- **arsnova-backend-core** — rooms, contents, answers, live socket
- **arsnova-auth-service** — authentication/authorization (JWT)
- **arsnova-comment-service** — Q&A / audience questions
- **arsnova-formatting-service** — Markdown/LaTeX rendering
- **couchdb** — primary datastore (CouchDB 3.5)
- **postgresql_auth**, **postgresql_comment** — service databases
- **rabbitmq** — STOMP message broker (core ↔ websocket gateway)

## Routing

Traefik publishes everything on a single host name and forwards the WebSocket
upgrade transparently. The front proxy dispatches internally:

- `https://<host>/` → web client
- `https://<host>/api/` → HTTP gateway
- `https://<host>/api/ws/` → WebSocket gateway (live features)

## Install

From the NethServer 8 cluster leader:

```bash
add-module ghcr.io/tebbiworld/arsnova:latest 1
```

Configure it (replace the host name):

```bash
api-cli run module/arsnova1/configure-module --data '{
  "host": "arsnova.example.org",
  "lets_encrypt": true,
  "http2https": true,
  "admin_email": "you@example.org"
}'
```

Open `https://arsnova.example.org`, register an account and verify it. ARSnova
sends the verification code by e-mail via the cluster smarthost. ARSnova's core
only supports a plain SMTP relay (port 25, no authentication); if no usable
relay is configured the code is written to the core logs:

```bash
journalctl --user -u arsnova-core.service | grep -i "verification\|code"
```

Set `admin_email` to the address of an already-registered user to grant it
administrator rights.

> ARSnova is resource hungry (Particify recommends 4 CPU / 8 GB RAM). On smaller
> nodes the Java services start slowly and may restart a few times before the
> stack settles.

## Build

```bash
bash build-images.sh
buildah push ghcr.io/tebbiworld/arsnova:latest
```

## Uninstall

```bash
remove-module --no-preserve arsnova1
```

## Disclaimer & trademarks

This is an **unofficial, community-built** NethServer 8 package. It is not
affiliated with or endorsed by Particify or the ARSnova team. "ARSnova" and
"Particify" are trademarks of their respective owners and are used here only to
identify the packaged software.

It self-hosts the upstream open-source components, pulled at runtime from Docker
Hub (not redistributed by this module):

- ARSnova server (core, authz, comments, websocket, gateway, formatting) —
  GPL-3.0-or-later
- ARSnova web client — MIT (© ARSnova Team and Contributors); the module logo is
  the official app icon from that MIT-licensed project
- CouchDB (Apache-2.0), PostgreSQL (PostgreSQL License), RabbitMQ (MPL-2.0),
  nginx proxy (BSD)

## License

This module's own code is GPL-3.0-or-later.

## Directory login (AD/LDAP)

Optional, in the settings under "Directory login". Two sources, the same
settings as the other tebbiworld modules (ns8-clamav, ns8-idevice-backup):

- **User domain of this cluster** (recommended). Only the domain name is
  stored; the module is bound to the domain as account consumer
  (`cluster:accountconsumer`) and reads the connection through the node's
  `ldapproxy` every time the core starts, so a new bind password or a moved
  domain controller is picked up by a restart (event `user-domain-changed`).
  An external AD/LDAP can be added to NS8 as a user domain too
  (*Domains and users*); it then shows up here.
- **LDAP server of its own** (advanced): URL, base DN, bind DN and password
  (kept in `state/passwords.env`, never returned by `get-configuration`; an
  empty field keeps the stored password), directory type, login attribute and
  the certificate check.

Optionally only members of one group may log in (Active Directory and Samba,
nested groups count). ARSnova's backend checks the login with Spring Security
LDAP, which only knows a user search filter; therefore:

- no StartTLS: use `ldaps://` (or `ldap://` in a trusted network);
- no group restriction for OpenLDAP (rfc2307) directories: their groups list
  `memberUid` values, which a user filter cannot test;
- a group given by name is resolved to its DN when the core starts; if the
  directory is unreachable then, the last known DN is used.

With the certificate check **on**, the core trusts the public CAs of its Java
runtime and checks the host name. With the check **off**, it trusts the
certificate the server presents when the core starts and skips the host name
check (the behaviour before 1.3.0, kept for updated installations). Updated
installations also keep the user filter of 1.2.0 (`(&(<attribute>={0})(memberOf=<group DN>))`,
direct membership only) until the directory settings are changed.

### How the core reaches the directory

The containers of a rootless Podman network can reach neither the node's
loopback nor the node's own IP address.

- For a **user domain**, the module user's pasta maps the node loopback to
  `169.254.1.3` (`~/.config/containers/containers.conf`, written only while a
  user domain is in use), and the core connects to the node's `ldapproxy`
  there. Side effect: while that mapping exists, the ARSnova containers can
  reach every service that listens on the node loopback. Switching to or away
  from a user domain restarts the whole module once, because the option only
  applies to a new rootless network.
- For a **server of its own** on this node (for example the NS8 Samba DC),
  the core gets an `--add-host <name>:host-gateway` entry: the host name and
  with it the certificate check stay intact. An IP address of this node is
  replaced by `host.containers.internal` (then turn the certificate check off).

