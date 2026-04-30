#! /bin/sh

qserver-list-plans-devices --startup-script startup.py
start-re-manager --startup-script=./startup.py --existing-plans-devices=./existing_plans_and_devices.yaml --user-group-permissions=./user_group_permissions.yaml --redis-addr redis:6379 --zmq-publish-console ON
