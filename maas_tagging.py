#!/usr/bin/env python

from __future__ import (
    unicode_literals,
    )

str = None

import ConfigParser
import os

try:
    import json
except ImportError:
    import simplejson as json

from apiclient.maas_client import (
    MAASClient,
    MAASDispatcher,
    MAASOAuth,
    )


class MaasTagging(object):

    def __init__(self):
        """ Main execution path """
        self.conn = None
        self.read_settings()
        self.run()

    def _connect(self):
        if not self.conn:
            auth = MAASOAuth(*self.maas_api_key.split(':'))
            dispatcher = MAASDispatcher()
            self.maas_client = MAASClient(auth, dispatcher, self.maas_url)
            self.conn = True

    def read_settings(self):
        """ Reads the settings from the maansible.ini file """

        config = ConfigParser.SafeConfigParser()
        config.read(os.path.dirname(os.path.realpath(__file__)) + '/maansible.ini')

        self.maas_url = config.get('maas', 'url')
        self.maas_api_key = config.get('maas', 'api_key')

	self.tags = dict(config.items('tags'))

    def run(self):
        """ Make calls to Maas to create tags and assign nodes to them """

        self._connect()

        # Get system ids of nodes
        nodes = self.maas_client.get('/nodes/', 'list').read()
        system_ids = {}
        for node in json.loads(nodes):
            system_ids[node['hostname'].split('.')[0]] = node['system_id']

        # Get existing tags
        tags = self.maas_client.get('/tags/', 'list').read()
        tags = [tag['name'] for tag in json.loads(tags)]

        # Create tags if not existing and apply them
        for tag in self.tags:
            if not tag in tags:
                params = {'name': tag}
                self.maas_client.post('/tags/', 'new', **params)
            nodes = self.tags[tag].split(',')
            for node in nodes:
                params = {'add': system_ids[node]}
                self.maas_client.post('/tags/%s/' % tag, 'update_nodes', **params)

MaasTagging()

