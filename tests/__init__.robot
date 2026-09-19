*** Settings ***
Library           SSHLibrary
Suite Setup       Connect to the node

*** Variables ***
${SSH_KEYFILE}    %{HOME}/.ssh/id_ecdsa
# install tests the image on a clean node; update installs ${UPDATE_FROM}
# first, then upgrades to the image under test. The CI passes both with -v.
${SCENARIO}       install

*** Keywords ***
Connect to the node
    Open Connection   ${NODE_ADDR}
    Login With Public Key    root    ${SSH_KEYFILE}
    ${output} =    Execute Command    systemctl is-system-running  --wait
    Should Be True    '${output}' == 'running' or '${output}' == 'degraded'
