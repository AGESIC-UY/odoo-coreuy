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

from base import SoapClientBase

class SoapSiceFacturaAjuste(SoapClientBase):
    """ GRP SICE Web Service Factura Ajuste"""

    #Begin Alta -------------------------------------------------------------------------------------------------
    def _prepare_request_alta(self, post_data):
        """
            @params post_data:
                {
                    See Documentation: Canal de Compras - Integración GRPs -v3.pdf. Page: 190
                }
        """
        return post_data

    def request_alta(self, model, cr, uid, ids, post_data, context=None):
        """
            Método que ejecuta el servicio de orden factura ajuste: alta
            @see _prepare_request_alta
        """
        if not isinstance(post_data, (dict,)):
            raise Exception("Se espera un diccionario como valor de retorno. Se ha recibido el tipo: %s" % (type(post_data),))
        url = model.pool.get('ir.config_parameter').get_param(cr, uid, 'url_ws.sice_facturas_ajuste', context=context)
        if not url:
            raise Exception(u'No se encuentra configurada la conexión con SICE.\n \
                Ir a: Configuración -> Parámetros -> Parámetros del sistema y cargar un registro \
                con clave url_ws.sice_facturas_ajuste y valor la URL del servicio web.')
        self.ensure_connection(url=url, msg_attr = 'Servicio: Factura Ajuste > Alta')
        _request = self._prepare_request_alta(post_data)
        #Response
        return self.client.service.alta(_request)
    #End Alta ---------------------------------------------------------------------------------------------------

    #Begin Modificar -----------------------------------------------------------------------------------------------
    def _prepare_request_modificar(self, post_data):
        """
            @params post_data:
                {
                    See Documentation: Canal de Compras - Integración GRPs -v3.pdf. Page: 196
                }
        """
        return post_data

    def request_modificar(self, model, cr, uid, ids, post_data, context=None):
        """
            Método que ejecuta el servicio de orden factura ajuste: modificar
            @see _prepare_request_modificar
        """
        if not isinstance(post_data, (dict,)):
            raise Exception("Se espera un diccionario como valor de retorno. Se ha recibido el tipo: %s" % (type(post_data),))
        url = model.pool.get('ir.config_parameter').get_param(cr, uid, 'url_ws.sice_facturas_ajuste', context=context)
        if not url:
            raise Exception(u'No se encuentra configurada la conexión con SICE.\n \
                Ir a: Configuración -> Parámetros -> Parámetros del sistema y cargar un registro \
                con clave url_ws.sice_facturas_ajuste y valor la URL del servicio web.')
        self.ensure_connection(url=url, msg_attr = 'Servicio: Factura Ajuste > Modificar')
        _request = self._prepare_request_modificar(post_data)
        #Response
        return self.client.service.modificar(_request)
    #End Modificar --------------------------------------------------------------------------------------------------

    #Begin Eliminar ---------------------------------------------------------------------------------------------------
    def _prepare_request_eliminar(self, post_data):
        """
            @params post_data:
                {
                    See Documentation: Canal de Compras - Integración GRPs -v3.pdf. Page: 198
                }
        """
        return post_data

    def request_eliminar(self, model, cr, uid, ids, post_data, context=None):
        """
            Método que ejecuta el servicio de orden factura ajuste: eliminar
            @see _prepare_request_eliminar
        """
        # if not isinstance(post_data, (dict,)):
        #     raise Exception("Se espera un diccionario como valor de retorno. Se ha recibido el tipo: %s" % (type(post_data),))
        url = model.pool.get('ir.config_parameter').get_param(cr, uid, 'url_ws.sice_facturas_ajuste', context=context)
        if not url:
            raise Exception(u'No se encuentra configurada la conexión con SICE.\n \
                Ir a: Configuración -> Parámetros -> Parámetros del sistema y cargar un registro \
                con clave url_ws.sice_facturas_ajuste y valor la URL del servicio web.')
        self.ensure_connection(url=url, msg_attr = 'Servicio: Factura Ajuste > Eliminar')
        _request = self._prepare_request_eliminar(post_data)
        #Response
        return self.client.service.eliminar(_request)
    #End Eliminar -------------------------------------------------------------------------------------------------------

    #Begin Aprobar ---------------------------------------------------------------------------------------------------
    def _prepare_request_aprobar(self, post_data):
        """
            @params post_data:
                {
                    See Documentation: Canal de Compras - Integración GRPs -v3.pdf. Page: 199
                }
        """
        return post_data

    def request_aprobar(self, model, cr, uid, ids, post_data, context=None):
        """
            Método que ejecuta el servicio de orden factura ajuste: aprobar
            @see _prepare_request_aprobar
        """
        # if not isinstance(post_data, (dict,)):
        #     raise Exception("Se espera un diccionario como valor de retorno. Se ha recibido el tipo: %s" % (type(post_data),))
        url = model.pool.get('ir.config_parameter').get_param(cr, uid, 'url_ws.sice_facturas_ajuste', context=context)
        if not url:
            raise Exception(u'No se encuentra configurada la conexión con SICE.\n \
                Ir a: Configuración -> Parámetros -> Parámetros del sistema y cargar un registro \
                con clave url_ws.sice_facturas_ajuste y valor la URL del servicio web.')
        self.ensure_connection(url=url, msg_attr = 'Servicio: Factura Ajuste > Aprobar')
        _request = self._prepare_request_aprobar(post_data)
        #Response
        return self.client.service.aprobar(_request)
    #End Aprobar -------------------------------------------------------------------------------------------------------

    #Begin Cambiar Estado ------------------------------------------------------------------------------------------------
    def _prepare_request_cambiar_estado(self, post_data):
        """
            @params post_data:
                {
                    See Documentation: Canal de Compras - Integración GRPs -v3.pdf. Page: 200
                }
        """
        return post_data

    def request_cambiar_estado(self, model, cr, uid, ids, post_data, context=None):
        """
            Método que ejecuta el servicio de orden factura ajuste: cambiar estado
            @see _prepare_request_cambiar_estado
        """
        # if not isinstance(post_data, (dict,)):
        #     raise Exception("Se espera un diccionario como valor de retorno. Se ha recibido el tipo: %s" % (type(post_data),))
        url = model.pool.get('ir.config_parameter').get_param(cr, uid, 'url_ws.sice_facturas_ajuste', context=context)
        if not url:
            raise Exception(u'No se encuentra configurada la conexión con SICE.\n \
                Ir a: Configuración -> Parámetros -> Parámetros del sistema y cargar un registro \
                con clave url_ws.sice_facturas_ajuste y valor la URL del servicio web.')
        self.ensure_connection(url=url, msg_attr = 'Servicio: Factura Ajuste > Cambiar Estado')
        _request = self._prepare_request_cambiar_estado(post_data)
        #Response
        return self.client.service.cambiarEstado(_request)
    #End Cambiar Estado ----------------------------------------------------------------------------------------------------

    #Begin Consultar -------------------------------------------------------------------------------------------------------
    def _prepare_request_consultar(self, post_data):
        """
            @params post_data:
                {
                    See Documentation: Canal de Compras - Integración GRPs -v3.pdf. Page: 202
                }
        """
        return post_data

    def request_consultar(self, model, cr, uid, ids, post_data, context=None):
        """
            Método que ejecuta el servicio de orden factura ajuste: consultar
            @see _prepare_request_consultar
        """
        # if not isinstance(post_data, (dict,)):
        #     raise Exception("Se espera un diccionario como valor de retorno. Se ha recibido el tipo: %s" % (type(post_data),))
        url = model.pool.get('ir.config_parameter').get_param(cr, uid, 'url_ws.sice_facturas_ajuste', context=context)
        if not url:
            raise Exception(u'No se encuentra configurada la conexión con SICE.\n \
                Ir a: Configuración -> Parámetros -> Parámetros del sistema y cargar un registro \
                con clave url_ws.sice_facturas_ajuste y valor la URL del servicio web.')
        self.ensure_connection(url=url, msg_attr = 'Servicio: Factura Ajuste > Consultar')
        _request = self._prepare_request_consultar(post_data)
        #Response
        return self.client.service.consultar(_request)
    #End Consultar ---------------------------------------------------------------------------------------------------------

    #Begin Listar ---------------------------------------------------------------------------------------------------------
    def _prepare_request_listar(self, post_data):
        """
            @params post_data:
                {
                    See Documentation: Canal de Compras - Integración GRPs -v3.pdf. Page: 202
                }
        """
        return post_data

    def request_listar(self, model, cr, uid, ids, post_data, context=None):
        """
            Método que ejecuta el servicio de orden factura ajuste: listar
            @see _prepare_request_listar
        """
        if not isinstance(post_data, (dict,)):
            raise Exception("Se espera un diccionario como valor de retorno. Se ha recibido el tipo: %s" % (type(post_data),))
        url = model.pool.get('ir.config_parameter').get_param(cr, uid, 'url_ws.sice_facturas_ajuste', context=context)
        if not url:
            raise Exception(u'No se encuentra configurada la conexión con SICE.\n \
                Ir a: Configuración -> Parámetros -> Parámetros del sistema y cargar un registro \
                con clave url_ws.sice_facturas_ajuste y valor la URL del servicio web.')
        self.ensure_connection(url=url, msg_attr = 'Servicio: Factura Ajuste > Listar')
        _request = self._prepare_request_listar(post_data)
        #Response
        return self.client.service.listar(_request)
    #End Listar -----------------------------------------------------------------------------------------------------------