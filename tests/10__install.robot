*** Settings ***
Library     SSHLibrary
Resource    api.resource

*** Variables ***
${CONFIG}    {"host":"arsnova.ci.test","lets_encrypt":false,"http2https":true,"admin_email":"admin@ci.test","allow_registration":true,"smtp_host":"","smtp_from":"","ldap_enabled":false}

*** Test Cases ***
Install the module
    IF    '${SCENARIO}' == 'update'
        ${output}  ${rc} =    Execute Command    add-module ${UPDATE_FROM} 1    return_rc=True
    ELSE
        ${output}  ${rc} =    Execute Command    add-module ${IMAGE_URL} 1    return_rc=True
    END
    Should Be Equal As Integers    ${rc}  0
    &{output} =    Evaluate    ${output}
    Set Global Variable    ${module_id}    ${output.module_id}

Configure the module
    Run task    module/${module_id}/configure-module    ${CONFIG}    decode_json=${FALSE}

ARSnova answers behind Traefik
    Wait Until Keyword Succeeds    90 times    10 seconds    Web client and API are served

Update to the image under test
    Skip If    '${SCENARIO}' != 'update'    scenario is ${SCENARIO}
    Run on node    api-cli run update-module --data '{"force":true,"module_url":"${IMAGE_URL}","instances":["${module_id}"]}'
    Wait Until Keyword Succeeds    90 times    10 seconds    Web client and API are served

Configuration reads back
    ${cfg} =    Run task    module/${module_id}/get-configuration    {}
    Should Be Equal    ${cfg['host']}    arsnova.ci.test
    Should Be Equal    ${cfg['admin_email']}    admin@ci.test
    Should Be True    ${cfg['allow_registration']}

No unit failed
    ${out} =    Run on node    runagent -m ${module_id} systemctl --user --failed --no-legend | wc -l
    Should Be Equal As Integers    ${out.strip()}    0

Secrets are stored in passwords.env only
    Secrets are kept out of the module environment    ${module_id}

*** Keywords ***
Web client and API are served
    ${out} =    Run on node    curl -fsSk -H 'Host: arsnova.ci.test' https://127.0.0.1/
    Should Contain    ${out}    <app-root
    # the backend is up when the gateway can reach core: guest login creates a token
    ${code} =    Run on node    curl -sSk -o /dev/null -w '\%{http_code}' -X POST -H 'Host: arsnova.ci.test' https://127.0.0.1/api/auth/login/guest
    Should Be Equal As Strings    ${code.strip()}    200
