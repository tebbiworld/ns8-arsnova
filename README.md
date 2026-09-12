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
- **couchdb** — primary datastore
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

## Directory server on the same node

If the LDAP/AD server is the node itself (for example the NS8 Samba account
provider on this node), the core container cannot connect to the node's own IP
address — rootless containers see that address as their own. The module detects
this at configuration time and points the core at `host.containers.internal`
instead; nothing needs to be configured for it. The detection runs again on
every module update.
