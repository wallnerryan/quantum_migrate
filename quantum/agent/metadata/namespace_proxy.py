# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright 2012 New Dream Network, LLC (DreamHost)
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
# @author: Mark McClain, DreamHost

import httplib
import socket
import urlparse

import eventlet
import httplib2
from oslo.config import cfg
import webob

from quantum.agent.linux import daemon
from quantum.common import config
from quantum.common import utils
from quantum.openstack.common import log as logging
from quantum import wsgi

proxy_socket = cfg.StrOpt('metadata_proxy_socket',
                          default='$state_path/metadata_proxy',
                          help=_('Location of Metadata Proxy UNIX domain '
                                 'socket'))

cfg.CONF.register_opt(proxy_socket)

LOG = logging.getLogger(__name__)


class UnixDomainHTTPConnection(httplib.HTTPConnection):
    """Connection class for HTTP over UNIX domain socket."""
    def __init__(self, host, port=None, strict=None, timeout=None,
                 proxy_info=None):
        httplib.HTTPConnection.__init__(self, host, port, strict)
        self.timeout = timeout

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        if self.timeout:
            self.sock.settimeout(self.timeout)
        self.sock.connect(cfg.CONF.metadata_proxy_socket)


class NetworkMetadataProxyHandler(object):
    """Proxy AF_INET metadata request through Unix Domain socket.

       The Unix domain socket allows the proxy access resource that are not
       accessible within the isolated tenant context.
    """

    def __init__(self, network_id=None, router_id=None):
        self.network_id = network_id
        self.router_id = router_id

        if network_id is None and router_id is None:
            msg = _('network_id and router_id are None. One must be provided.')
            raise ValueError(msg)

    @webob.dec.wsgify(RequestClass=wsgi.Request)
    def __call__(self, req):
        LOG.debug(_("Request: %s"), req)
        try:
            return self._proxy_request(req.remote_addr,
                                       req.method,
                                       req.path_info,
                                       req.query_string,
                                       req.body)
        except Exception:
            LOG.exception(_("Unexpected error."))
            msg = _('An unknown error has occurred. '
                    'Please try your request again.')
            return webob.exc.HTTPInternalServerError(explanation=unicode(msg))

    def _proxy_request(self, remote_address, method, path_info,
                       query_string, body):
        headers = {
            'X-Forwarded-For': remote_address,
        }

        if self.router_id:
            headers['X-Quantum-Router-ID'] = self.router_id
        else:
            headers['X-Quantum-Network-ID'] = self.network_id

        url = urlparse.urlunsplit((
            'http',
            '169.254.169.254',  # a dummy value to make the request proper
            path_info,
            query_string,
            ''))

        h = httplib2.Http()
        resp, content = h.request(
            url,
            method=method,
            headers=headers,
            body=body,
            connection_type=UnixDomainHTTPConnection)

        if resp.status == 200:
            LOG.debug(resp)
            LOG.debug(content)
            return content
        elif resp.status == 404:
            return webob.exc.HTTPNotFound()
        elif resp.status == 409:
            return webob.exc.HTTPConflict()
        elif resp.status == 500:
            msg = _(
                'Remote metadata server experienced an internal server error.'
            )
            LOG.debug(msg)
            return webob.exc.HTTPInternalServerError(explanation=unicode(msg))
        else:
            raise Exception(_('Unexpected response code: %s') % resp.status)


class ProxyDaemon(daemon.Daemon):
    def __init__(self, pidfile, port, network_id=None, router_id=None):
        uuid = network_id or router_id
        super(ProxyDaemon, self).__init__(pidfile, uuid=uuid)
        self.network_id = network_id
        self.router_id = router_id
        self.port = port

    def run(self):
        handler = NetworkMetadataProxyHandler(
            self.network_id,
            self.router_id)
        proxy = wsgi.Server('quantum-network-metadata-proxy')
        proxy.start(handler, self.port)
        proxy.wait()


def main():
    eventlet.monkey_patch()
    opts = [
        cfg.StrOpt('network_id'),
        cfg.StrOpt('router_id'),
        cfg.StrOpt('pid_file'),
        cfg.BoolOpt('daemonize', default=True),
        cfg.IntOpt('metadata_port',
                   default=9697,
                   help=_("TCP Port to listen for metadata server "
                          "requests.")),
    ]

    cfg.CONF.register_cli_opts(opts)
    # Don't get the default configuration file
    cfg.CONF(project='quantum', default_config_files=[])
    config.setup_logging(cfg.CONF)
    utils.log_opt_values(LOG)
    proxy = ProxyDaemon(cfg.CONF.pid_file,
                        cfg.CONF.metadata_port,
                        network_id=cfg.CONF.network_id,
                        router_id=cfg.CONF.router_id)

    if cfg.CONF.daemonize:
        proxy.start()
    else:
        proxy.run()
