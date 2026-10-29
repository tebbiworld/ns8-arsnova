#!/usr/local/agent/pyenv/bin/python3

#
# Copyright (C) 2026 tebbi
# SPDX-License-Identifier: GPL-3.0-or-later
#

"""Functional smoke test of an ARSnova instance, run on the node.

Usage: arsnova_functest.py <host> seed|check <state.json>

  seed   guest A creates a room with a published choice question and turns
         Q&A on; guest B joins, votes and posts a question (comment), which
         must reach A over the STOMP websocket; the ids go to state.json
  check  a new guest joins the seeded room and reads the room, the question,
         the vote count and the comment back (after an update or restore)

Talks to Traefik on 127.0.0.1 with the given Host header (the certificate
is self-signed in CI). Uses the agent's Python environment, which ships
requests and aiohttp. Exit code 0 means every step passed; the only
credentials involved are throwaway guest tokens, which are not printed.
"""

import asyncio
import base64
import json
import sys
import time

import aiohttp
import requests

BASE = "https://127.0.0.1/api"
WS_URL = "wss://127.0.0.1/api/ws/websocket"  # SockJS raw websocket endpoint
ROOM_NAME = "Functest room"
QUESTION = "Functest question?"
COMMENT = "Functest comment"
TIMEOUT = 30
STARTUP_TRIES = 90
# the services start one after the other: the gateway answers 5xx while the
# one behind a route is still booting
UNAVAILABLE_TRIES = 30
UNAVAILABLE_PAUSE = 10


class Api:
    def __init__(self, host):
        self.host = host
        self.session = requests.Session()
        self.session.verify = False
        requests.packages.urllib3.disable_warnings()

    def call(self, method, path, token=None, body=None):
        headers = {"Host": self.host, "Content-Type": "application/json", "Accept": "application/json"}
        if token:
            headers["Authorization"] = "Bearer " + token
        data = json.dumps(body) if body is not None else None
        for _ in range(UNAVAILABLE_TRIES):
            resp = self.session.request(method, BASE + path, headers=headers, timeout=60, data=data)
            if resp.status_code < 500:
                break
            time.sleep(UNAVAILABLE_PAUSE)
        if resp.status_code >= 400:
            sys.exit(f"FAIL {method} {path}: HTTP {resp.status_code} {resp.text[:300]}")
        return resp.json() if resp.text.strip().startswith(("{", "[")) else None

    def guest(self):
        return self.call("POST", "/auth/login/guest")["token"]

    def wait_until_up(self):
        for _ in range(STARTUP_TRIES):
            try:
                if self.session.post(BASE + "/auth/login/guest", headers={"Host": self.host},
                                     timeout=10).status_code == 200:
                    return
            except requests.RequestException:
                pass
            time.sleep(10)
        sys.exit("FAIL the API did not answer")


def user_id(token):
    payload = token.split(".")[1]
    return json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))["sub"]


async def expect_comment_event(host, token, room_id, post_comment):
    """Subscribe to the comment stream of the room over STOMP, post the
    comment, wait for the MESSAGE frame the comment service publishes."""
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(WS_URL, ssl=False, headers={"Host": host}, timeout=TIMEOUT) as ws:
            # no STOMP "host" header: the gateway would pass it on as RabbitMQ vhost
            await ws.send_str(f"CONNECT\naccept-version:1.2\ntoken:{token}\n\n\x00")
            frame = await asyncio.wait_for(ws.receive(), TIMEOUT)
            if not str(frame.data).startswith("CONNECTED"):
                sys.exit(f"FAIL websocket CONNECT: {str(frame.data)[:200]}")
            await ws.send_str(f"SUBSCRIBE\nid:sub-0\ndestination:/topic/{room_id}.comment.stream\n\n\x00")
            await asyncio.sleep(2)  # let the relay set up the subscription
            await asyncio.get_running_loop().run_in_executor(None, post_comment)
            deadline = time.time() + TIMEOUT
            while time.time() < deadline:
                frame = await asyncio.wait_for(ws.receive(), deadline - time.time())
                if str(frame.data).startswith("MESSAGE"):
                    return
    sys.exit("FAIL websocket: no comment event")


def seed(api, state_file):
    owner = api.guest()
    room = api.call("POST", "/room/", owner, {"name": ROOM_NAME})
    room_id = room["id"]
    content = api.call("POST", f"/room/{room_id}/content/", owner, {
        "roomId": room_id, "format": "CHOICE", "body": QUESTION,
        "options": [{"label": "yes"}, {"label": "no"}], "correctOptionIndexes": [], "multiple": False})
    api.call("POST", f"/room/{room_id}/contentgroup/-/content/", owner,
             {"roomId": room_id, "contentGroupName": "Functest", "contentId": content["id"]})
    group = api.call("GET", f"/room/{room_id}/stats?view=read-extended", owner)["groupStats"][0]
    api.call("PATCH", f"/room/{room_id}/contentgroup/{group['id']}", owner, {"published": True})
    # Q&A is off in a new room: the owner switches it on
    settings = api.call("GET", f"/room/{room_id}/settings/{room_id}", owner)
    settings["disabled"] = False
    api.call("PUT", f"/room/{room_id}/settings/{room_id}", owner, settings)

    participant = api.guest()
    api.call("POST", f"/room/{room_id}/request-membership", participant, {})
    api.call("POST", f"/room/{room_id}/answer/", participant, {
        "format": "CHOICE", "contentId": content["id"], "roomId": room_id, "round": 1,
        "selectedChoiceIndexes": [0]})
    comment = {}
    asyncio.run(expect_comment_event(api.host, owner, room_id, lambda: comment.update(api.call(
        "POST", f"/room/{room_id}/comment/", participant,
        {"roomId": room_id, "creatorId": user_id(participant), "body": COMMENT}))))
    print("seed ok: room created, question published, vote counted, comment pushed over the websocket")
    with open(state_file, "w") as fp:
        json.dump({"room_id": room_id, "content_id": content["id"], "comment_id": comment["id"]}, fp)


def vote_count(api, token, room_id, content_id):
    """Votes for the first option. The core counts answers asynchronously
    (CouchDB view, cached): give a fresh vote a little time to show up."""
    for _ in range(TIMEOUT):
        stats = api.call("GET", f"/room/{room_id}/content/{content_id}/stats", token)
        votes = stats["roundStatistics"][0]["independentCounts"][0]
        if votes:
            return votes
        time.sleep(2)
    return votes


def check(api, state_file):
    with open(state_file) as fp:
        state = json.load(fp)
    room_id = state["room_id"]
    reader = api.guest()
    api.call("POST", f"/room/{room_id}/request-membership", reader, {})
    room = api.call("GET", f"/room/{room_id}", reader)
    content = api.call("GET", f"/room/{room_id}/content/{state['content_id']}", reader)
    comment = api.call("GET", f"/room/{room_id}/comment/{state['comment_id']}", reader)
    votes = vote_count(api, reader, room_id, state["content_id"])
    if room["name"] != ROOM_NAME or content["body"] != QUESTION or votes != 1 or comment["body"] != COMMENT:
        sys.exit(f"FAIL data differs: room={room['name']!r} question={content['body']!r} "
                 f"votes={votes} comment={comment['body']!r}")
    print(f"check ok: room {room['shortId']}, question, 1 vote and the comment are there")


def main():
    if len(sys.argv) != 4 or sys.argv[2] not in ("seed", "check"):
        sys.exit(__doc__)
    api = Api(sys.argv[1])
    api.wait_until_up()
    (seed if sys.argv[2] == "seed" else check)(api, sys.argv[3])


if __name__ == "__main__":
    main()
