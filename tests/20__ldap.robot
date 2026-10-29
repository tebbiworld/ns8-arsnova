*** Settings ***
Library     SSHLibrary
Library     Collections
Resource    api.resource

*** Variables ***
${LDAP_CUSTOM}    "ldap_enabled":true,"ldap_title":"CI","ldap_source":"custom","ldap_url":"ldaps://ldap.ci.test:636","ldap_start_tls":false,"ldap_tls_verify":true,"ldap_schema":"ad","ldap_base_dn":"DC=ci,DC=test","ldap_bind_dn":"CN=svc,DC=ci,DC=test","ldap_user_attribute":"","ldap_group":"CN=arsnova,DC=ci,DC=test"
${BAD_TITLE}      "ldap_title":"CI\\nX=1"
# the core answers through Traefik; curl gives up after 90 s (prints 000)
${LDAP_LOGIN}     curl -sk -o /dev/null -w '\%{http_code} \%{time_total}' --max-time 90 -H 'Host: arsnova.ci.test' -H 'Content-Type: application/json' -d '{"loginId":"ci-user","password":"Ci-wrong-Pass1"}' https://127.0.0.1/api/auth/login/ldap || true
${BASE}           "host":"arsnova.ci.test","lets_encrypt":false,"http2https":true,"admin_email":"admin@ci.test","allow_registration":true,"smtp_host":"","smtp_from":""

*** Test Cases ***
The bind password never leaves the module
    ${cfg} =    Run task    module/${module_id}/get-configuration    {}
    Dictionary Should Not Contain Key    ${cfg}    ldap_bind_password
    Should Be True    ${cfg['ldap_bind_password_set']}
    ${out} =    Run on node    api-cli run module/${module_id}/get-configuration --data '{}'
    Should Not Contain    ${out}    Ci-bind-Pass1

An empty password field keeps the stored password
    Configure    {${BASE},${LDAP_CUSTOM},"ldap_bind_password":""}
    ${cfg} =    Run task    module/${module_id}/get-configuration    {}
    Should Be True    ${cfg['ldap_bind_password_set']}
    ${stored} =    Run on node    runagent -m ${module_id} grep -c '^LDAP_BIND_PASSWORD=Ci-bind-Pass1$' passwords.env
    Should Be Equal As Integers    ${stored.strip()}    1

The core gets the directory settings
    Wait Until Keyword Succeeds    30 times    10 seconds    Core is active
    ${mode} =    Run on node    runagent -m ${module_id} stat -c %a ldap.env
    Should Be Equal As Strings    ${mode.strip()}    600
    ${env} =    Run on node    runagent -m ${module_id} grep -E '^SECURITY_AUTHENTICATIONPROVIDERS_LDAP_0_(ENABLED|HOSTURL|USERSEARCHFILTER|CONNECTTIMEOUT)=' ldap.env
    Should Contain    ${env}    ENABLED=true
    # without it the provider list from the environment has timeout 0 (wait for TCP)
    Should Contain    ${env}    CONNECTTIMEOUT=5000
    Should Contain    ${env}    HOSTURL=ldaps://ldap.ci.test:636/DC=ci,DC=test
    # nested groups count (LDAP_MATCHING_RULE_IN_CHAIN), disabled accounts do not
    Should Contain    ${env}    (memberOf:1.2.840.113556.1.4.1941:=CN=arsnova,DC=ci,DC=test)
    Should Contain    ${env}    userAccountControl:1.2.840.113556.1.4.803:=2
    # certificate check on: no pinned store, no host name exception
    ${java} =    Run on node    runagent -m ${module_id} grep -c disableEndpointIdentification ldap.env || true
    Should Be Equal As Integers    ${java.strip()}    0

Certificate check off pins the server certificate
    Configure    {${BASE},${LDAP_CUSTOM},"ldap_tls_verify":false,"ldap_bind_password":""}
    Wait Until Keyword Succeeds    30 times    10 seconds    Core is active
    ${java} =    Run on node    runagent -m ${module_id} grep -c disableEndpointIdentification ldap.env
    Should Be Equal As Integers    ${java.strip()}    1

An unreachable server fails the login quickly
    # 192.0.2.1 (TEST-NET-1) never answers: the login must end with the
    # connect timeout of 5 s, not with a gateway timeout (504) after 60 s
    Configure    {${BASE},${LDAP_CUSTOM},"ldap_url":"ldaps://192.0.2.1:636","ldap_bind_password":""}
    Wait Until Keyword Succeeds    90 times    10 seconds    Directory login is answered
    ${result} =    Run on node    ${LDAP_LOGIN}
    ${code}    ${seconds} =    Evaluate    $result.split()
    Should Be Equal As Strings    ${code}    401
    Should Be True    float($seconds) < 30    login took ${seconds} s

ARSnova limits are refused
    Configuration is refused    {${BASE},${LDAP_CUSTOM},"ldap_url":"ldap://ldap.ci.test:389","ldap_start_tls":true,"ldap_bind_password":""}    start_tls_unsupported
    Configuration is refused    {${BASE},${LDAP_CUSTOM},"ldap_schema":"rfc2307","ldap_bind_password":""}    group_needs_ad
    Configuration is refused    {${BASE},${LDAP_CUSTOM},${BAD_TITLE},"ldap_bind_password":""}    ldap_value_invalid

A user domain must exist in the cluster
    Configuration is refused    {${BASE},"ldap_enabled":true,"ldap_title":"CI","ldap_source":"domain","ldap_domain":"no-such-domain.ci.test","ldap_group":""}    ldap_domain_unknown

Directory login off
    # the settings page always sends every field, the server settings stay stored
    Configure    {${BASE},${LDAP_CUSTOM},"ldap_enabled":false,"ldap_bind_password":""}
    ${off} =    Run on node    runagent -m ${module_id} grep -c '^SECURITY_AUTHENTICATIONPROVIDERS_LDAP' ldap.env || true
    Should Be Equal As Integers    ${off.strip()}    0
    ${conf} =    Run on node    test -e /home/${module_id}/.config/containers/containers.conf && echo present || echo absent
    Should Be Equal As Strings    ${conf.strip()}    absent
    Wait Until Keyword Succeeds    90 times    10 seconds    Web client and API are served

*** Keywords ***
Configure
    [Arguments]    ${input}
    Run task    module/${module_id}/configure-module    ${input}    decode_json=${FALSE}

Configuration is refused
    [Arguments]    ${input}    ${error}
    ${stdout}    ${stderr}    ${rc} =    Execute Command    api-cli run module/${module_id}/configure-module --data '${input}'    return_stdout=True    return_stderr=True    return_rc=True    timeout=5 min
    Should Not Be Equal As Integers    ${rc}    0    configure-module accepted ${input}
    Should Contain    ${stdout}${stderr}    ${error}

Core is active
    ${state} =    Run on node    runagent -m ${module_id} systemctl --user is-active arsnova-core.service
    Should Be Equal As Strings    ${state.strip()}    active

Directory login is answered
    # the core is up and offers the LDAP provider (not 502/503 while it starts)
    ${result} =    Run on node    ${LDAP_LOGIN}
    Should Not Match Regexp    ${result}    ^(000|404|502|503)    login not answered yet: ${result}

Web client and API are served
    ${out} =    Run on node    curl -fsSk -H 'Host: arsnova.ci.test' https://127.0.0.1/
    Should Contain    ${out}    <app-root
    ${code} =    Run on node    curl -sSk -o /dev/null -w '\%{http_code}' -X POST -H 'Host: arsnova.ci.test' https://127.0.0.1/api/auth/login/guest
    Should Be Equal As Strings    ${code.strip()}    200
