<!--
First community post for the NS8 ARSnova module, written in the style
of https://community.nethserver.org/t/ns8-forgejo-testing/28554 (first post).
Paste into a new topic on community.nethserver.org, category "App", tag "ns8".
Fill in the wiki link once the page is published.
-->

# NS8 ARSnova (testing)

Hi all,

I've built an NS8 module for [ARSnova / Particify](https://github.com/particify/arsnova) — a live audience-response and interactive-learning system (polls, quizzes, Q&A, live feedback) you can run for your own classroom, lecture or meeting.

It's in my community repository. To try it, add the repo once:

```
api-cli run add-repository --data '{"name":"tebbiworld","url":"https://raw.githubusercontent.com/tebbiworld/ns8-repo/main/ns8/updates/","status":true,"testing":false}'
```

then install **ARSnova** from the Software Center. (Or straight from the image: `add-module ghcr.io/tebbiworld/arsnova:latest 1`.)

What it does:

* Runs the full Particify/ARSnova stack — live polls, quizzes, audience Q&A and real-time feedback — behind a single host name, with WebSocket live updates forwarded transparently through Traefik.
* Publishes everything on one FQDN with optional Let's Encrypt and HTTP→HTTPS redirection.
* Optional Active Directory / LDAP login, including restricting access to a single AD group, so people sign in with their existing accounts.
* Self-registration can be switched on or off; you can also promote an existing user to administrator from the settings.

A few things to know:

* It's a proper microservice stack (around a dozen containers: the Spring-Boot services, CouchDB, two PostgreSQL databases, a RabbitMQ broker, the web client and a front proxy), so it wants some headroom — Particify suggest roughly 4 CPU / 8 GB RAM. On smaller nodes the Java services start slowly and may restart a few times before everything settles.
* If you rely on email verification for local sign-up, you'll need a usable SMTP relay; ARSnova's core only speaks plain SMTP on port 25 with no auth, otherwise the verification code lands in the logs.
* Unofficial and community-built — not affiliated with or endorsed by Particify or the ARSnova team.

Still very much testing, so I'd love a second pair of eyes — if you give it a go, let me know how it behaves on your hardware and whether AD/LDAP login works cleanly for you.

Docs: NethServer wiki (tebbiworld repository) · Source: [github.com/tebbiworld/ns8-arsnova](https://github.com/tebbiworld/ns8-arsnova)

Thanks!

*Category: App · Tags: ns8*
