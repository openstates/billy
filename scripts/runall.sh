#!/usr/bin/env bash
# Copyright (c) Sunlight Foundation, 2014, BSD-3

if [ ! -d logs ]; then
    mkdir -p logs
fi

for state in $(ls *py | sed 's/\.py//g'); do
    echo -n "[    ]  ${state}"
    python -m pupa.cli update ${state} $@ >logs/${state}.log 2>&1
    RET=$?
    if [ "x${RET}" = "x0" ]; then
        echo -e "\r[ [32mok[0m ]"
    else
        echo -e "\r[[31mfail[0m]"
    fi
done
