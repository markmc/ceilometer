# -*- encoding: utf-8 -*-
#
# Copyright © 2012 New Dream Network, LLC (DreamHost)
#
# Author: Doug Hellmann <doug.hellmann@dreamhost.com>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
"""Publish a counter using the preferred RPC mechanism.
"""

import itertools

from oslo.config import cfg

from ceilometer.collector import meter as meter_api
from ceilometer.openstack.common import log
from ceilometer.openstack.common import rpc
from ceilometer import plugin

LOG = log.getLogger(__name__)

PUBLISH_OPTS = [
    cfg.StrOpt('metering_topic',
               default='metering',
               help='the topic ceilometer uses for metering messages',
               ),
]


class MeterPublisher(plugin.PublisherBase):
    def publish_counters(self, conf, context, counters, source):
        """Send a metering message for publishing

        :param context: Execution context from the service or RPC call
        :param counter: Counter from pipeline after transformation
        :param source: counter source
        """

        conf.register_opts(PUBLISH_OPTS)
        meter_api.register_opts(conf)

        meters = [
            meter_api.meter_message_from_counter(counter,
                                                 conf.metering_secret,
                                                 source)
            for counter in counters
        ]

        # FIXME(markmc): cache this?
        rpc_impl = rpc.get_impl(conf)

        topic = conf.metering_topic
        msg = {
            'method': 'record_metering_data',
            'version': '1.0',
            'args': {'data': meters},
        }
        LOG.debug('PUBLISH: %s', str(msg))
        rpc_impl.cast(conf, context, topic, msg)

        for meter_name, meter_list in itertools.groupby(
                sorted(meters, key=lambda m: m['counter_name']),
                lambda m: m['counter_name']):
            msg = {
                'method': 'record_metering_data',
                'version': '1.0',
                'args': {'data': list(meter_list)},
            }
            rpc_impl.cast(conf, context, topic + '.' + meter_name, msg)
