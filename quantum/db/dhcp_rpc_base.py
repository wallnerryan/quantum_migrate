# Copyright (c) 2012 OpenStack Foundation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from oslo.config import cfg
from sqlalchemy.orm import exc

from quantum.api.v2 import attributes
from quantum.common import constants
from quantum.common import utils
from quantum import manager
from quantum.openstack.common import log as logging


LOG = logging.getLogger(__name__)


class DhcpRpcCallbackMixin(object):
    """A mix-in that enable DHCP agent support in plugin implementations."""

    def get_active_networks(self, context, **kwargs):
        """Retrieve and return a list of the active network ids."""
        host = kwargs.get('host')
        LOG.debug(_('Network list requested from %s'), host)
        plugin = manager.QuantumManager.get_plugin()
        if utils.is_extension_supported(
            plugin, constants.AGENT_SCHEDULER_EXT_ALIAS):
            if cfg.CONF.network_auto_schedule:
                plugin.auto_schedule_networks(context, host)
            nets = plugin.list_active_networks_on_active_dhcp_agent(
                context, host)
        else:
            filters = dict(admin_state_up=[True])
            nets = plugin.get_networks(context, filters=filters)
        return [net['id'] for net in nets]

    def get_network_info(self, context, **kwargs):
        """Retrieve and return a extended information about a network."""
        network_id = kwargs.get('network_id')
        host = kwargs.get('host')
        LOG.debug(_('Network %(network_id)s requested from '
                    '%(host)s'), {'network_id': network_id,
                                  'host': host})
        plugin = manager.QuantumManager.get_plugin()
        network = plugin.get_network(context, network_id)

        filters = dict(network_id=[network_id])
        network['subnets'] = plugin.get_subnets(context, filters=filters)
        network['ports'] = plugin.get_ports(context, filters=filters)
        return network

    def get_dhcp_port(self, context, **kwargs):
        """Allocate a DHCP port for the host and return port information.

        This method will re-use an existing port if one already exists.  When a
        port is re-used, the fixed_ip allocation will be updated to the current
        network state.

        """
        host = kwargs.get('host')
        network_id = kwargs.get('network_id')
        device_id = kwargs.get('device_id')
        # There could be more than one dhcp server per network, so create
        # a device id that combines host and network ids

        LOG.debug(_('Port %(device_id)s for %(network_id)s requested from '
                    '%(host)s'), {'device_id': device_id,
                                  'network_id': network_id,
                                  'host': host})
        plugin = manager.QuantumManager.get_plugin()
        retval = None

        filters = dict(network_id=[network_id])
        subnets = dict([(s['id'], s) for s in
                        plugin.get_subnets(context, filters=filters)])

        dhcp_enabled_subnet_ids = [s['id'] for s in
                                   subnets.values() if s['enable_dhcp']]

        try:
            filters = dict(network_id=[network_id], device_id=[device_id])
            ports = plugin.get_ports(context, filters=filters)
            if len(ports):
                # Ensure that fixed_ips cover all dhcp_enabled subnets.
                port = ports[0]
                for fixed_ip in port['fixed_ips']:
                    if fixed_ip['subnet_id'] in dhcp_enabled_subnet_ids:
                        dhcp_enabled_subnet_ids.remove(fixed_ip['subnet_id'])
                port['fixed_ips'].extend(
                    [dict(subnet_id=s) for s in dhcp_enabled_subnet_ids])

                retval = plugin.update_port(context, port['id'],
                                            dict(port=port))

        except exc.NoResultFound:
            pass

        if retval is None:
            # No previous port exists, so create a new one.
            LOG.debug(_('DHCP port %(device_id)s on network %(network_id)s '
                        'does not exist on %(host)s'), locals())

            network = plugin.get_network(context, network_id)

            port_dict = dict(
                admin_state_up=True,
                device_id=device_id,
                network_id=network_id,
                tenant_id=network['tenant_id'],
                mac_address=attributes.ATTR_NOT_SPECIFIED,
                name='',
                device_owner='network:dhcp',
                fixed_ips=[dict(subnet_id=s) for s in dhcp_enabled_subnet_ids])

            retval = plugin.create_port(context, dict(port=port_dict))

        # Convert subnet_id to subnet dict
        for fixed_ip in retval['fixed_ips']:
            subnet_id = fixed_ip.pop('subnet_id')
            fixed_ip['subnet'] = subnets[subnet_id]

        return retval

    def release_dhcp_port(self, context, **kwargs):
        """Release the port currently being used by a DHCP agent."""
        host = kwargs.get('host')
        network_id = kwargs.get('network_id')
        device_id = kwargs.get('device_id')

        LOG.debug(_('DHCP port deletion for %(network_id)s request from '
                    '%(host)s'), locals())
        plugin = manager.QuantumManager.get_plugin()
        filters = dict(network_id=[network_id], device_id=[device_id])
        ports = plugin.get_ports(context, filters=filters)

        if len(ports):
            plugin.delete_port(context, ports[0]['id'])

    def release_port_fixed_ip(self, context, **kwargs):
        """Release the fixed_ip associated the subnet on a port."""
        host = kwargs.get('host')
        network_id = kwargs.get('network_id')
        device_id = kwargs.get('device_id')
        subnet_id = kwargs.get('subnet_id')

        LOG.debug(_('DHCP port remove fixed_ip for %(subnet_id)s request '
                    'from %(host)s'), locals())
        plugin = manager.QuantumManager.get_plugin()
        filters = dict(network_id=[network_id], device_id=[device_id])
        ports = plugin.get_ports(context, filters=filters)

        if len(ports):
            port = ports[0]

            fixed_ips = port.get('fixed_ips', [])
            for i in range(len(fixed_ips)):
                if fixed_ips[i]['subnet_id'] == subnet_id:
                    del fixed_ips[i]
                    break
            plugin.update_port(context, port['id'], dict(port=port))

    def update_lease_expiration(self, context, **kwargs):
        """Release the fixed_ip associated the subnet on a port."""
        host = kwargs.get('host')
        network_id = kwargs.get('network_id')
        ip_address = kwargs.get('ip_address')
        lease_remaining = kwargs.get('lease_remaining')

        LOG.debug(_('Updating lease expiration for %(ip_address)s on network '
                    '%(network_id)s from %(host)s.'), locals())
        plugin = manager.QuantumManager.get_plugin()

        plugin.update_fixed_ip_lease_expiration(context, network_id,
                                                ip_address, lease_remaining)
