#!/usr/bin/env python

from __future__ import (
    unicode_literals,
    )

str = None

import argparse
import ConfigParser
import os
import re
from time import time

try:
    import json
except ImportError:
    import simplejson as json

from apiclient.maas_client import (
    MAASClient,
    MAASDispatcher,
    MAASOAuth,
    )


class MaasInventory(object):

    def __init__(self):
        """ Main execution path """
        self.conn = None

        self.inventory = dict()  # A list of groups and the hosts in that group
        self.cache = dict()  # Details about hosts in the inventory

        # Read settings and parse CLI arguments
        self.read_settings()
        self.parse_cli_args()

        # Cache
        if self.args.refresh_cache:
            self.update_cache()
        elif not self.is_cache_valid():
            self.update_cache()
        else:
            self.load_inventory_from_cache()
            self.load_cache_from_cache()

        data_to_print = ""

        # Data to print
        if self.args.host:
            data_to_print = self.get_host_info()

        elif self.args.list:
            # Display list of instances for inventory
            data_to_print = self.json_format_dict(self.inventory, True)

        else:  # default action with no options
            data_to_print = self.json_format_dict(self.inventory, True)

        print data_to_print

    def _connect(self):
        if not self.conn:
            auth = MAASOAuth(*self.maas_api_key.split(':'))
            dispatcher = MAASDispatcher()
            self.maas_client = MAASClient(auth, dispatcher, self.maas_url)
            self.conn = True

    def is_cache_valid(self):
        """ Determines if the cache files have expired, or if it is still valid """

        if os.path.isfile(self.cache_path_cache):
            mod_time = os.path.getmtime(self.cache_path_cache)
            current_time = time()
            if (mod_time + self.cache_max_age) > current_time:
                if os.path.isfile(self.cache_path_inventory):
                    return True

        return False

    def read_settings(self):
        """ Reads the settings from the maansible.ini file """

        config = ConfigParser.SafeConfigParser()
        config.read(os.path.dirname(os.path.realpath(__file__)) + '/maansible.ini')

        self.maas_url = config.get('maas', 'url')
        self.maas_api_key = config.get('maas', 'api_key')

        self.tags = dict(config.items('tags'))

        family = dict(config.items('family'))
        groups = []
        for parent in family:
            group = {
                'name': parent,
                'children': family[parent].split(','),
                'vars': dict(config.items(parent+':vars'))
            }
            groups.append(group)
        self.ansible_groups = groups

        host_vars = dict(config.items('host:vars'))
        host_vars['devices'] = host_vars['devices'].split(',')
        host_vars['raw_journal_devices'] = host_vars['raw_journal_devices'].split(',')
        self.ansible_host_vars = host_vars

        # Cache related
        cache_path = config.get('maas', 'cache_path')
        self.cache_path_cache = cache_path + "/ansible-maas.cache"
        self.cache_path_inventory = cache_path + "/ansible-maas.index"
        self.cache_max_age = config.getint('maas', 'cache_max_age')

    def parse_cli_args(self):
        """ Command line argument processing """

        parser = argparse.ArgumentParser(description='Produce an Ansible Inventory file based on Maas')
        parser.add_argument('--list', action='store_true', default=True, help='List instances (default: True)')
        parser.add_argument('--host', action='store', help='Get all the variables about a specific instance')
        parser.add_argument('--refresh-cache', action='store_true', default=False,
                            help='Force refresh of cache by making API requests to Maas (default: False - use cache files)')
        self.args = parser.parse_args()

    def update_cache(self):
        """ Make calls to Maas and save the output in a cache """

        self._connect()
        self.groups = dict()
        self.hosts = dict()

        hostvars = dict()
        for tag in self.tags:
            nodes = self.maas_client.get('/tags/' + tag, 'nodes').read()
            nodes = json.loads(nodes)
            hosts = []
            for node in nodes:
                hostname = node['hostname']
                ip_address = node['ip_addresses'][0]
                if not hostname in hostvars:
                    hostvars[hostname] = dict()
                    hostvars[hostname].update(self.ansible_host_vars)
                    hostvars[hostname]['ansible_ssh_host'] = ip_address
                hosts.append(hostname)
            self.inventory[tag] = {'hosts': hosts}
        self.inventory['_meta'] = {'hostvars': hostvars}

        for group in self.ansible_groups:
            self.inventory[group['name']] = {
                'children': group['children'],
                'vars': group['vars']
            }

        self.write_to_cache(self.cache, self.cache_path_cache)
        self.write_to_cache(self.inventory, self.cache_path_inventory)

    def get_host_info(self):
        """ Get variables about a specific host """

        if not self.cache or len(self.cache) == 0:
            # Need to load index from cache
            self.load_cache_from_cache()

        if not self.args.host in self.cache:
            # try updating the cache
            self.update_cache()

            if not self.args.host in self.cache:
                # host might not exist anymore
                return self.json_format_dict({}, True)

        return self.json_format_dict(self.cache[self.args.host], True)

    def push(self, my_dict, key, element):
        """ Pushed an element onto an array that may not have been defined in the dict """

        if key in my_dict:
            my_dict[key].append(element)
        else:
            my_dict[key] = [element]

    def load_inventory_from_cache(self):
        """ Reads the index from the cache file sets self.index """

        cache = open(self.cache_path_inventory, 'r')
        json_inventory = cache.read()
        self.inventory = json.loads(json_inventory)

    def load_cache_from_cache(self):
        """ Reads the cache from the cache file sets self.cache """

        cache = open(self.cache_path_cache, 'r')
        json_cache = cache.read()
        self.cache = json.loads(json_cache)

    def write_to_cache(self, data, filename):
        """ Writes data in JSON format to a file """

        json_data = self.json_format_dict(data, True)
        cache = open(filename, 'w')
        cache.write(json_data)
        cache.close()

    def to_safe(self, word):
        """ Converts 'bad' characters in a string to underscores so they can be used as Ansible groups """

        return re.sub("[^A-Za-z0-9\-]", "_", word)

    def json_format_dict(self, data, pretty=False):
        """ Converts a dict to a JSON object and dumps it as a formatted string """

        if pretty:
            return json.dumps(data, sort_keys=True, indent=2)
        else:
            return json.dumps(data)

MaasInventory()

