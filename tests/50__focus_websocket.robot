*** Settings ***
Library     SSHLibrary
Resource    api.resource
Documentation
...    The live/focus features use a STOMP WebSocket whose endpoint is Spring
...    SockJS, which runs a same-origin check on the handshake. Behind Traefik
...    the request reaches the front proxy over plain http, so without the
...    X-Forwarded-Proto/-Port pinning the gateway rejects the browser's https
...    Origin with 403 and focus mode stays stuck on the welcome page. These
...    cases ask the SockJS endpoint through the instance's own published port
...    (as Traefik does: real public Host, no usable scheme hint), exactly where
...    the bug showed, independent of what the CI's Traefik forwards.

*** Variables ***
${PUBLIC_ORIGIN}      https://arsnova.ci.test
${PUBLIC_HOST}        arsnova.ci.test
${FOREIGN_ORIGIN}     https://evil.example.org

*** Test Cases ***
The SockJS handshake accepts the instance's own browser Origin
    [Documentation]    Positive: a browser Origin equal to the instance's public
    ...                URL must pass. On the stock (unpatched) proxy the gateway
    ...                sees an http origin and answers 403; with the fix it is
    ...                200. Retried because the stack may still be settling.
    Wait Until Keyword Succeeds    30 times    10 seconds
    ...    SockJS info status is    ${PUBLIC_ORIGIN}    200

A foreign browser Origin is still refused
    [Documentation]    Negative control: the fix must not turn into "allow any
    ...                origin". A different site's Origin stays a 403.
    SockJS info status is    ${FOREIGN_ORIGIN}    403

*** Keywords ***
SockJS info status is
    [Arguments]    ${origin}    ${expected}
    ${port} =    Run on node    runagent -m ${module_id} printenv TCP_PORT
    ${code} =    Run on node
    ...    curl -s -o /dev/null -w '%{http_code}' --max-time 10 -H 'Host: ${PUBLIC_HOST}' -H 'Origin: ${origin}' http://127.0.0.1:${port.strip()}/api/ws/info
    Should Be Equal As Strings    ${code.strip()}    ${expected}
    ...    SockJS /api/ws/info with Origin ${origin} returned ${code.strip()}, expected ${expected}
