# Maansible

This project is an attempt to integrate MAAS and Ansible.  Only tested with acaleph-ansible.

## Files

maansible.ini - A shared config file by maas_inventory.py and maas_tagging.py.

maansible.sh - A sample script on how to run this project.

maas_inventory.py - Based on ansible/plugins/inventory/cobbler.py, this produces a JSON-formatted inventory to be fed to the ansible-playbook command.

maas_tagging.py - A script to assign hosts to groups as needed by Ansible.

## To Do

* Integration with MAAS UI
* A fully automated way to assign hosts to groups
* Make it more generic
