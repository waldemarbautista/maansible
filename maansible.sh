#!/bin/bash

./maas_tagging.py
cd acaleph-ansible
ansible-playbook -i ../maas_inventory.py site.yml
