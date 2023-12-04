#!/bin/bash

function init {
    check_deps
    create_env
}
function run {
    python PDUtilities
    return
}
function create_env {
    python -m venv env > /dev/null
    activate_env
    if [ $? -ne 0 ]; then _error "Couldn't activate virtualenv"; fi
    python -m pip install -r requirements.txt
    return
}
function activate_env {
    source $(find ./env -name "activate")
    return $?
}

# TODO: The way I made this function is giving me AIDS, please correct this...
function check_deps {
    command -v python > /dev/null
    if [ $? -ne 0 ]; then
        _error "Python 3 must be installed in order to run."
    fi

    python -m pip --version
    if [ $? -ne 0 ]; then
        _error "pip for Python3 could not be found."
    fi

    python -m venv -h > /dev/null
    if [ $? -ne 0 ]; then
        echo "Installing virtualenv..."
        python -m pip install virtualenv
        if [ $? -ne 0 ]; then _error "Couldn't install 'virtualenv'"; fi
    fi

    return
}

function clean {
    rm -rf ./env/
    return
}
function build {
    return
}

_error() {
    echo $1
    exit 1
}

if [ "$1" == "clean" ]; then clean; fi

activate_env
if [ $? -ne 0 ]; then
    init
fi
run

if [ "$1" == "build" ]; then build; fi