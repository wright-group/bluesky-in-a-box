#! /bin/sh

qserver-list-plans-devices --startup-script startup.py
/usr/local/bin/start-re-manager --startup-script=./startup.py --existing-plans-devices=./existing_plans_and_devices.yaml --user-group-permissions=./user_group_permissions.yaml --zmq-data-proxy-addr zmq-proxy:5567 --redis-addr redis:6379 --zmq-publish-console ON

