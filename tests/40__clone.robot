*** Settings ***
Library     SSHLibrary
Resource    api.resource

*** Test Cases ***
Free the memory of the restored instance
    # the original instance is stopped since the restore test; two full
    # ARSnova stacks do not fit into the CI guest
    Run on node    runagent -m ${restored_id} systemctl --user stop arsnova.service

Clone the module
    [Documentation]    "Clone and Move" is a platform behaviour: the core copies
    ...                volumes and state/, the module re-creates its route through
    ...                clone-module/50configure_module.
    ${out} =    Run task    cluster/clone-module    {"module":"${module_id}","replace":false,"node":1}
    Set Global Variable    ${clone_id}    ${out['module_id']}
    Should Not Be Equal    ${clone_id}    ${module_id}

The clone has its route, settings and secrets
    ${orig} =    Run task    module/traefik1/get-route    {"instance":"${module_id}"}
    ${route} =    Run task    module/traefik1/get-route    {"instance":"${clone_id}"}
    Should Be Equal    ${route['host']}    ${orig['host']}
    Should Not Be Equal    ${route['url']}    ${orig['url']}
    ${cfg} =    Run task    module/${clone_id}/get-configuration    {}
    Should Be Equal    ${cfg['admin_email']}    admin@ci.test
    Secrets are kept out of the module environment    ${clone_id}
    # only values that are set count: configure-module may add empty entries
    ${a} =    Run on node    runagent -m ${module_id} bash -c 'grep -v "=$" "$AGENT_STATE_DIR/passwords.env" | sort | sha256sum'
    ${b} =    Run on node    runagent -m ${clone_id} bash -c 'grep -v "=$" "$AGENT_STATE_DIR/passwords.env" | sort | sha256sum'
    Should Be Equal    ${a}    ${b}

The clone serves the data of the original
    # the volumes are copied as they are: the room, vote and comment of the
    # install test and the probe rows; asked through the clone's own front
    # proxy, because the original and the restored instance keep their routes
    # for the same host name
    ${port} =    Run on node    runagent -m ${clone_id} printenv TCP_PORT
    ${out} =    Run on node    /usr/local/agent/pyenv/bin/python3 /root/arsnova_functest.py arsnova.ci.test check /root/arsnova_functest.json http://127.0.0.1:${port.strip()}
    Log    ${out}
    ${note} =    Run on node    runagent -m ${clone_id} podman exec postgresql_comment psql -U arsnovacomment -d arsnovacomment -tAc "SELECT note FROM ci_probe"
    Should Be Equal    ${note.strip()}    pre-backup

Remove the clone
    Run on node    remove-module --no-preserve ${clone_id}
