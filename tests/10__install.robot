*** Settings ***
Library     SSHLibrary
Resource    api.resource

*** Variables ***
# The LDAP fields are those of a client before 1.3.0 (no ldap_source): an
# LDAP server entered by hand. The update scenario checks its migration.
${CONFIG}    {"host":"arsnova.ci.test","lets_encrypt":false,"http2https":true,"admin_email":"admin@ci.test","allow_registration":true,"smtp_host":"","smtp_from":"","ldap_enabled":true,"ldap_url":"ldaps://ldap.ci.test:636","ldap_base_dn":"DC=ci,DC=test","ldap_bind_dn":"CN=svc,DC=ci,DC=test","ldap_bind_password":"Ci-bind-Pass1","ldap_group":"CN=arsnova,DC=ci,DC=test","ldap_user_attribute":"sAMAccountName","ldap_title":"CI"}

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

Manual LDAP settings of the previous release are migrated
    Skip If    '${SCENARIO}' != 'update'    scenario is ${SCENARIO}
    ${cfg} =    Run task    module/${module_id}/get-configuration    {}
    Should Be Equal    ${cfg['ldap_source']}    custom
    Should Be Equal    ${cfg['ldap_url']}    ldaps://ldap.ci.test:636
    Should Be Equal    ${cfg['ldap_group']}    CN=arsnova,DC=ci,DC=test
    # the certificate stays pinned without host name check, as before
    Should Not Be True    ${cfg['ldap_tls_verify']}
    Should Be True    ${cfg['ldap_bind_password_set']}
    ${old_keys} =    Run on node    grep -Ec '^LDAP_(HOST|PORT)=' /home/${module_id}/.config/state/environment || true
    Should Be Equal As Integers    ${old_keys.strip()}    0
    # the user filter of 1.2.0 stays until the settings are changed
    ${filter} =    Run on node    runagent -m ${module_id} grep '^SECURITY_AUTHENTICATIONPROVIDERS_LDAP_0_USERSEARCHFILTER=' ldap.env
    Should Be Equal As Strings    ${filter.strip()}    SECURITY_AUTHENTICATIONPROVIDERS_LDAP_0_USERSEARCHFILTER=(&(sAMAccountName={0})(memberOf=CN=arsnova,DC=ci,DC=test))

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
