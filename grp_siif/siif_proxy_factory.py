# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Enterprise Management Solution
#    GRP Estado Uruguay
#    Copyright (C) 2017 Quanam (ATEL SA., Uruguay)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import codecs
import locale
import sys
import os
from suds.client import Client
from suds.cache import NoCache
from suds.plugin import MessagePlugin
import ssl
from functools import wraps
from openerp import models, api
from openerp.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)

class LogPlugin(MessagePlugin):

    def marshalled(self, context):
        pass
        #_logger.info('marshalled:')
        #_logger.info(str(context.envelope))

    def sending(self, context):
        pass
        #_logger.warning('ENVIADO:')
        #_logger.warning(str(context.envelope))

    def received(self, context):
        pass
        #_logger.warning('RECIBIDO:')
        #_logger.warning(str(context.reply))

#LogPlugin()

# Fix de TLS_1 (python por defecto usa TLS_2 y el servidor no lo soporta), fuente: http://stackoverflow.com/a/24166498/1603788
def sslwrap(func):
    @wraps(func)
    def bar(*args, **kw):
        kw['ssl_version'] = ssl.PROTOCOL_TLSv1
        return func(*args, **kw)

    return bar
ssl.wrap_socket = sslwrap(ssl.wrap_socket)

# Fix al WSDL
# Se agrega la linea:
# <import namespace="http://schemas.xmlsoap.org/soap/encoding/" />
#como primer hijo de <schema>
class siif_proxy_factory(models.AbstractModel):
    _name = 'siif.proxy.factory'

    _proxy = False
    @property
    def proxy(self):
        return self._proxy
    @proxy.setter
    def proxy(self, value):
        self._proxy = value
    @proxy.deleter
    def proxy(self):
        del self._proxy

    _local_wsdl = False
    @property
    def local_wsdl(self):
        return self._local_wsdl
    @local_wsdl.setter
    def local_wsdl(self, value):
        self._local_wsdl = value
    @local_wsdl.deleter
    def local_wsdl(self):
        del self._local_wsdl

    @api.model
    def _get_siif(self, retornaXML=False, unverified_context=False, check_wsdl=False):
        """
        Establece la conexión con el WS y crea el objeto SOAP cliente de dicha conexión.
        """
        if not check_wsdl: #Web
            self.local_wsdl = False
            # Obtener la URL de parámetros del sistema
            url_siif = self.env['ir.config_parameter'].get_param('url_ws.siif', '')
            if not url_siif or url_siif=='0':
                _logger.info('Servicio Web SIIF: No se pudo conectar con el servicio.')
                return False, 'Error!\n %s' % ('No se encuentra configurada la ruta del WSDL para consumir los servicios SIIF',)
            # Establecer la conexión
            try:
                return True, Client(url_siif, cache=NoCache(), retxml=retornaXML)
            except Exception as e:
                return False, 'Error!\n %s' % ('Ha ocurrido un error en la comunicación web con SIIF',)
        else:
            self.local_wsdl = True
            try:
                sys.stdout = codecs.getwriter(locale.getpreferredencoding())(sys.stdout)
                path_file = os.path.dirname(os.path.abspath(__file__))
                ultima_barra =  path_file.rfind('/')
                path_new = path_file[:ultima_barra]
                if unverified_context:
                    try:
                        _create_unverified_https_context = ssl._create_unverified_context
                    except AttributeError:
                        # Legacy Python that doesn't verify HTTPS certificates by default
                        pass
                    else:
                        # Handle target environment that doesn't support HTTPS verification
                        ssl._create_default_https_context = _create_unverified_https_context
                # Construcción del objeto clente SOAP
                url = 'file://' + path_new + '/CGNSiiF.wsdl'
                return True, Client(url, plugins=[LogPlugin()], cache=NoCache(), retxml=retornaXML)
            except Exception as e:
                return False, 'Error!\n %s' % (u'Ha ocurrido un error en la comunicación local con SIIF',)

    @api.model
    def get_proxy(self, retornaXML=False, unverified_context=False, raise_exception=True, check_wsdl=False):
        """
        @param raise_exception: Si es True lanza un ValidationError en caso de ocurrir alguna excepción
        @param check_wsdl: Si es True y ocurre un error de comunicación web entonces lo intenta con el WSDL local
        """
        # #Todos se intenta por la web
        # result, client = self._get_siif(retornaXML=retornaXML)
        #
        # #Solo los que estén incluídos en el WSDL local
        # errors=[]
        # if not result and not check_wsdl:
        #     errors.append(client)
        # if not result and check_wsdl:
        #     errors.append(client)
        #     result, client = self._get_siif(retornaXML=retornaXML, unverified_context=unverified_context, check_wsdl=True)
        #     if not result:
        #         errors.append(client)

        errors = []
        result, client = self._get_siif(retornaXML=retornaXML, unverified_context=unverified_context, check_wsdl=check_wsdl)
        if not result:
            errors.append(client)

        #Retorna un cliente soap, True/False or ValidationError
        if result:
            self.proxy = client
            return self
        else:
            self.proxy = False
            if raise_exception and errors:
                raise ValidationError("Error: "+"\n".join(errors))
            return False

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
