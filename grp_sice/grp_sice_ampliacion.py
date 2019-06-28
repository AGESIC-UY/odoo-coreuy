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

class SoapSiceAmpliacion(SoapClientBase):
    """ GRP SICE Web Service Compra Ampliaciones """

    #Begin Alta -------------------------------------------------------------------------------------------------
    def _prepare_request_alta(self, post_data):
        """
            @params post_data:
                {
                    See Documentation: Canal de Compras - Integración GRPs -v3.pdf. Page: 128
                }
        """
        return post_data

    def request_alta(self, model, cr, uid, ids, post_data, context=None):
        """
            Método que ejecuta el servicio de compra ampliaciones: alta
            @see _prepare_request_alta
        """
        if not isinstance(post_data, (dict,)):
            raise Exception("Se espera un diccionario como valor de retorno. Se ha recibido el tipo: %s" % (type(post_data),))
        url = model.pool.get('ir.config_parameter').get_param(cr, uid, 'url_ws.sice_compras_ampliaciones', context=context)
        if not url:
            raise Exception(u'No se encuentra configurada la conexión con SICE.\n \
                Ir a: Configuración -> Parámetros -> Parámetros del sistema y cargar un registro \
                con clave url_ws.sice_compras_ampliaciones y valor la URL del servicio web.')
        self.ensure_connection(url=url, msg_attr = 'Servicio: Compra Ampliaciones > Alta')
        _request = self._prepare_request_alta(post_data)
        #Response
        return self.client.service.alta(_request)
    #End Alta ---------------------------------------------------------------------------------------------------

    #Begin Alta con Atributos -----------------------------------------------------------------------------------
    def _prepare_request_alta_attr(self, post_data):
        """
            @params post_data:
                {
                    See Documentation: Canal de Compras - Integración GRPs -v3.pdf. Page: 136
                }
        """
        return post_data

    def request_alta_attr(self, model, cr, uid, ids, post_data, context=None):
        """
            Método que ejecuta el servicio de compra ampliaciones: alta con atributos
            @see _prepare_request_alta_attr
        """
        if not isinstance(post_data, (dict,)):
            raise Exception("Se espera un diccionario como valor de retorno. Se ha recibido el tipo: %s" % (type(post_data),))
        url = model.pool.get('ir.config_parameter').get_param(cr, uid, 'url_ws.sice_compras_ampliaciones', context=context)
        if not url:
            raise Exception(u'No se encuentra configurada la conexión con SICE.\n \
                Ir a: Configuración -> Parámetros -> Parámetros del sistema y cargar un registro \
                con clave url_ws.sice_compras_ampliaciones y valor la URL del servicio web.')
        self.ensure_connection(url=url, msg_attr = 'Servicio: Compra Ampliaciones > Alta con Atributos')
        _request = self._prepare_request_alta_attr(post_data)
        #Response
        return self.client.service.altaConAtributos(_request)
    #End Alta con Atributos -------------------------------------------------------------------------------------

    #Begin Modificar --------------------------------------------------------------------------------------------
    def _prepare_request_modificar(self, post_data):
        """
            @params post_data:
                {
                    See Documentation: Canal de Compras - Integración GRPs -v3.pdf. Page: 128
                }
        """
        return post_data

    def request_modificar(self, model, cr, uid, ids, post_data, context=None):
        """
            Método que ejecuta el servicio de compra ampliaciones: modificar
            @see _prepare_request_modificar
        """
        if not isinstance(post_data, (dict,)):
            raise Exception("Se espera un diccionario como valor de retorno. Se ha recibido el tipo: %s" % (type(post_data),))
        url = model.pool.get('ir.config_parameter').get_param(cr, uid, 'url_ws.sice_compras_ampliaciones', context=context)
        if not url:
            raise Exception(u'No se encuentra configurada la conexión con SICE.\n \
                Ir a: Configuración -> Parámetros -> Parámetros del sistema y cargar un registro \
                con clave url_ws.sice_compras_ampliaciones y valor la URL del servicio web.')
        self.ensure_connection(url=url, msg_attr = 'Servicio: Compra Ampliaciones > Modificar')
        _request = self._prepare_request_modificar(post_data)
        #Response
        return self.client.service.modificar(_request)
    #End Modificar -----------------------------------------------------------------------------------------------

    #Begin Modificar con Atributos -------------------------------------------------------------------------------
    def _prepare_request_modificar_attr(self, post_data):
        """
            @params post_data:
                {
                    See Documentation: Canal de Compras - Integración GRPs -v3.pdf. Page: 145
                }
        """
        return post_data

    def request_modificar_attr(self, model, cr, uid, ids, post_data, context=None):
        """
            Método que ejecuta el servicio de compra ampliaciones: modificar con atributos
            @see _prepare_request_modificar_attr
        """
        if not isinstance(post_data, (dict,)):
            raise Exception("Se espera un diccionario como valor de retorno. Se ha recibido el tipo: %s" % (type(post_data),))
        url = model.pool.get('ir.config_parameter').get_param(cr, uid, 'url_ws.sice_compras_ampliaciones', context=context)
        if not url:
            raise Exception(u'No se encuentra configurada la conexión con SICE.\n \
                Ir a: Configuración -> Parámetros -> Parámetros del sistema y cargar un registro \
                con clave url_ws.sice_compras_ampliaciones y valor la URL del servicio web.')
        self.ensure_connection(url=url, msg_attr = 'Servicio: Compra Ampliaciones > Modificar con Atributos')
        _request = self._prepare_request_modificar_attr(post_data)
        #Response
        return self.client.service.modificarConAtributos(_request)
    #End Modificar con Atributos ---------------------------------------------------------------------------------

    #Begin Eliminar -------------------------------------------------------------------------------
    def _prepare_request_eliminar(self, post_data):
        """
            @params post_data:
                {
                    See Documentation: Canal de Compras - Integración GRPs -v3.pdf. Page: 145
                }
        """
        return post_data

    def request_eliminar(self, model, cr, uid, ids, post_data, context=None):
        """
            Método que ejecuta el servicio de compra ampliaciones: eliminar
            @see _prepare_request_aliminar
        """
        if not isinstance(post_data, (dict,)):
            raise Exception("Se espera un diccionario como valor de retorno. Se ha recibido el tipo: %s" % (type(post_data),))
        url = model.pool.get('ir.config_parameter').get_param(cr, uid, 'url_ws.sice_compras_ampliaciones', context=context)
        if not url:
            raise Exception(u'No se encuentra configurada la conexión con SICE.\n \
                Ir a: Configuración -> Parámetros -> Parámetros del sistema y cargar un registro \
                con clave url_ws.sice_compras_ampliaciones y valor la URL del servicio web.')
        self.ensure_connection(url=url, msg_attr = 'Servicio: Compra Ampliaciones > Eliminar')
        _request = self._prepare_request_eliminar(post_data)
        #Response
        return self.client.service.eliminar(_request)
    #End Eliminar ---------------------------------------------------------------------------------

    #Begin Aprobar -------------------------------------------------------------------------------
    def _prepare_request_aprobar(self, post_data):
        """
            @params post_data:
                {
                    See Documentation: Canal de Compras - Integración GRPs -v3.pdf. Page: 145
                }
        """
        return post_data

    def request_aprobar(self, model, cr, uid, ids, post_data, context=None):
        """
            Método que ejecuta el servicio de compra ampliaciones: aprobar
            @see _prepare_request_aprobar
        """
        # if not isinstance(post_data, (dict,)):
        #     raise Exception("Se espera un diccionario como valor de retorno. Se ha recibido el tipo: %s" % (type(post_data),))
        url = model.pool.get('ir.config_parameter').get_param(cr, uid, 'url_ws.sice_compras_ampliaciones', context=context)
        if not url:
            raise Exception(u'No se encuentra configurada la conexión con SICE.\n \
                Ir a: Configuración -> Parámetros -> Parámetros del sistema y cargar un registro \
                con clave url_ws.sice_compras_ampliaciones y valor la URL del servicio web.')
        self.ensure_connection(url=url, msg_attr = 'Servicio: Compra Ampliaciones > Aprobar')
        _request = self._prepare_request_aprobar(post_data)
        #Response
        return self.client.service.aprobar(_request)
    #End Aprobar ------------------------------------------------------------------------------------

    #Begin Aprobar con Atributos --------------------------------------------------------------------
    def _prepare_request_aprobar_attr(self, post_data):
        """
            @params post_data:
                {
                    See Documentation: Canal de Compras - Integración GRPs -v3.pdf. Page: 148
                }
        """
        return post_data

    def request_aprobar_attr(self, model, cr, uid, ids, post_data, context=None):
        """
            Método que ejecuta el servicio de compra ampliaciones: aprobar con atributos
            @see _prepare_request_aprobar_attr
        """
        if not isinstance(post_data, (dict,)):
            raise Exception("Se espera un diccionario como valor de retorno. Se ha recibido el tipo: %s" % (type(post_data),))
        url = model.pool.get('ir.config_parameter').get_param(cr, uid, 'url_ws.sice_compras_ampliaciones', context=context)
        if not url:
            raise Exception(u'No se encuentra configurada la conexión con SICE.\n \
                Ir a: Configuración -> Parámetros -> Parámetros del sistema y cargar un registro \
                con clave url_ws.sice_compras_ampliaciones y valor la URL del servicio web.')
        self.ensure_connection(url=url, msg_attr = 'Servicio: Compra Ampliaciones > Aprobar con Atributos')
        _request = self._prepare_request_aprobar_attr(post_data)
        #Response
        return self.client.service.aprobarConAtributos(_request)
    #End Aprobar con Atributos --------------------------------------------------------------------------

    #Begin Cambiar Estado --------------------------------------------------------------------
    def _prepare_request_cambiar_estado(self, post_data):
        """
            @params post_data:
                {
                    See Documentation: Canal de Compras - Integración GRPs -v3.pdf. Page: 148
                }
        """
        return post_data

    def request_cambiar_estado(self, model, cr, uid, ids, post_data, context=None):
        """
            Método que ejecuta el servicio de compra ampliaciones: cambiar estado
            @see _prepare_request_cambiar_estado
        """
        if not isinstance(post_data, (dict,)):
            raise Exception("Se espera un diccionario como valor de retorno. Se ha recibido el tipo: %s" % (type(post_data),))
        url = model.pool.get('ir.config_parameter').get_param(cr, uid, 'url_ws.sice_compras_ampliaciones', context=context)
        if not url:
            raise Exception(u'No se encuentra configurada la conexión con SICE.\n \
                Ir a: Configuración -> Parámetros -> Parámetros del sistema y cargar un registro \
                con clave url_ws.sice_compras_ampliaciones y valor la URL del servicio web.')
        self.ensure_connection(url=url, msg_attr = 'Servicio: Compra Ampliaciones > Cambiar Estado')
        _request = self._prepare_request_cambiar_estado(post_data)
        #Response
        return self.client.service.cambiarEstado(_request)
    #End Cambiar Estado --------------------------------------------------------------------------

    #Begin Cambiar Estado con Atributos ----------------------------------------------------------
    def _prepare_request_cambiar_estado_attr(self, post_data):
        """
            @params post_data:
                {
                    See Documentation: Canal de Compras - Integración GRPs -v3.pdf. Page: 149
                }
        """
        return post_data

    def request_cambiar_estado_attr(self, model, cr, uid, ids, post_data, context=None):
        """
            Método que ejecuta el servicio de compra ampliaciones: cambiar estado con atributos
            @see _prepare_request_cambiar_estado_attr
        """
        if not isinstance(post_data, (dict,)):
            raise Exception("Se espera un diccionario como valor de retorno. Se ha recibido el tipo: %s" % (type(post_data),))
        url = model.pool.get('ir.config_parameter').get_param(cr, uid, 'url_ws.sice_compras_ampliaciones', context=context)
        if not url:
            raise Exception(u'No se encuentra configurada la conexión con SICE.\n \
                Ir a: Configuración -> Parámetros -> Parámetros del sistema y cargar un registro \
                con clave url_ws.sice_compras_ampliaciones y valor la URL del servicio web.')
        self.ensure_connection(url=url, msg_attr = 'Servicio: Compra Ampliaciones > Cambiar Estado con Atributos')
        _request = self._prepare_request_cambiar_estado_attr(post_data)
        #Response
        return self.client.service.cambiarEstadoConAtributos(_request)
    #End Cambiar Estado con Atributos ------------------------------------------------------------------

    #Begin Consultar -----------------------------------------------------------------------------------
    def _prepare_request_consultar(self, post_data):
        """
            @params post_data:
                {
                    See Documentation: Canal de Compras - Integración GRPs -v3.pdf. Page: 149
                }
        """
        return post_data

    def request_consultar(self, model, cr, uid, ids, post_data, context=None):
        """
            Método que ejecuta el servicio de compra ampliaciones: consultar
            @see _prepare_request_consultar
        """
        # if not isinstance(post_data, (dict,)):
        #     raise Exception("Se espera un diccionario como valor de retorno. Se ha recibido el tipo: %s" % (type(post_data),))
        url = model.pool.get('ir.config_parameter').get_param(cr, uid, 'url_ws.sice_compras_ampliaciones', context=context)
        if not url:
            raise Exception(u'No se encuentra configurada la conexión con SICE.\n \
                Ir a: Configuración -> Parámetros -> Parámetros del sistema y cargar un registro \
                con clave url_ws.sice_compras_ampliaciones y valor la URL del servicio web.')
        self.ensure_connection(url=url, msg_attr = 'Servicio: Compra Ampliaciones > Consultar')
        _request = self._prepare_request_consultar(post_data)
        #Response
        return self.client.service.consultar(_request)
    #End Consultar ------------------------------------------------------------------------------------------

    #Begin Consultar con Atributos --------------------------------------------------------------------------
    def _prepare_request_consultar_attr(self, post_data):
        """
            @params post_data:
                {
                    See Documentation: Canal de Compras - Integración GRPs -v3.pdf. Page: 149
                }
        """
        return post_data

    def request_consultar_attr(self, model, cr, uid, ids, post_data, context=None):
        """
            Método que ejecuta el servicio de compra ampliaciones: consultar con atributos
            @see _prepare_request_consultar
        """
        # if not isinstance(post_data, (dict,)):
        #     raise Exception("Se espera un diccionario como valor de retorno. Se ha recibido el tipo: %s" % (type(post_data),))
        url = model.pool.get('ir.config_parameter').get_param(cr, uid, 'url_ws.sice_compras_ampliaciones', context=context)
        if not url:
            raise Exception(u'No se encuentra configurada la conexión con SICE.\n \
                Ir a: Configuración -> Parámetros -> Parámetros del sistema y cargar un registro \
                con clave url_ws.sice_compras_ampliaciones y valor la URL del servicio web.')
        self.ensure_connection(url=url, msg_attr = 'Servicio: Compra Ampliaciones > Consultar con Atributos')
        _request = self._prepare_request_consultar_attr(post_data)
        #Response
        return self.client.service.consultarConAtributos(_request)
    #End Consultar con Atributos ------------------------------------------------------------------------------

    #Begin Descargar Archivo ----------------------------------------------------------------------------------
    def _prepare_request_descargar_archivo(self, post_data):
        """
            @params post_data:
                {
                    See Documentation: Canal de Compras - Integración GRPs -v3.pdf. Page: 150
                }
        """
        return post_data

    def request_descargar_archivo(self, model, cr, uid, ids, post_data, context=None):
        """
            Método que ejecuta el servicio de compra ampliaciones: descargar archivo
            @see _prepare_request_consultar
        """
        if not isinstance(post_data, (dict,)):
            raise Exception("Se espera un diccionario como valor de retorno. Se ha recibido el tipo: %s" % (type(post_data),))
        url = model.pool.get('ir.config_parameter').get_param(cr, uid, 'url_ws.sice_compras_ampliaciones', context=context)
        if not url:
            raise Exception(u'No se encuentra configurada la conexión con SICE.\n \
                Ir a: Configuración -> Parámetros -> Parámetros del sistema y cargar un registro \
                con clave url_ws.sice_compras_ampliaciones y valor la URL del servicio web.')
        self.ensure_connection(url=url, msg_attr = 'Servicio: Compra Ampliaciones > Descargar Archivo')
        _request = self._prepare_request_descargar_archivo(post_data)
        #Response
        return self.client.service.descargarArchivo(_request)
    #End Descargar Archivo ---------------------------------------------------------------------------------------