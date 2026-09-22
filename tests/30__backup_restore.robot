*** Settings ***
Library     SSHLibrary
Resource    api.resource

*** Test Cases ***
Seed a probe row
    Run on node    runagent -m ${module_id} podman exec postgresql_comment psql -U arsnovacomment -d arsnovacomment -c "CREATE TABLE ci_probe (note text); INSERT INTO ci_probe VALUES ('pre-backup');"

Back up the module
    ${repo}    ${path} =    Back up the module to the cluster repository    ${module_id}
    Set Global Variable    ${BACKUP_REPO}    ${repo}
    Set Global Variable    ${BACKUP_PATH}    ${path}

Free the memory of the first instance
    # two full ARSnova pods do not fit into the CI guest
    Run on node    runagent -m ${module_id} systemctl --user stop arsnova.service

Restore into a new instance
    ${rid} =    Restore the module from the cluster repository    ${BACKUP_REPO}    ${BACKUP_PATH}
    Set Global Variable    ${restored_id}    ${rid}
    Should Not Be Equal    ${restored_id}    ${module_id}

The restored instance has data, settings and secrets
    ${out} =    Wait Until Keyword Succeeds    40 times    10 seconds
    ...    Run on node    runagent -m ${restored_id} podman exec postgresql_comment psql -U arsnovacomment -d arsnovacomment -tAc "SELECT note FROM ci_probe"
    Should Contain    ${out}    pre-backup
    ${cfg} =    Run task    module/${restored_id}/get-configuration    {}
    Should Be Equal    ${cfg['admin_email']}    admin@ci.test
    Secrets are kept out of the module environment    ${restored_id}
    # authz can only log in to its restored database with the restored password
    Wait Until Keyword Succeeds    60 times    10 seconds
    ...    Run on node    test "$(runagent -m ${restored_id} systemctl --user is-active arsnova-authz.service arsnova-comments.service arsnova-core.service | sort -u)" = active
