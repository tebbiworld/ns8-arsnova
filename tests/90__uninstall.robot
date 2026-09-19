*** Settings ***
Library     SSHLibrary
Resource    api.resource

*** Test Cases ***
Remove the restored instance
    Run on node    remove-module --no-preserve ${restored_id}

Remove the module
    Run on node    remove-module --no-preserve ${module_id}
