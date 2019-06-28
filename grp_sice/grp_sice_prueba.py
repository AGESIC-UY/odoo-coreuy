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
from openerp.exceptions import ValidationError

class SoapSicePrueba(SoapClientBase):
    """ GRP SICE Web Service Prueba """

    def _prepare_request_get_prueba(self, result):
        #self.ensure_connection(msg_attr = 'Servicio: Prueba > ConversionRate')
        # _request = self.client.factory.create('ConversionRate')
        # for key, value in result.items():
        #     if hasattr(_request, key):
        #         setattr(_request, key, value)
        # return _request
        return result

    def request_get_prueba(self, model, cr, uid, ids, post_data, context=None):
        if not isinstance(post_data, (dict,)):
            raise Exception("Se espera un diccionario como valor de retorno. Se ha recibido el tipo: %s" % (type(post_data),))
        #url = 'http://www.webservicex.com/currencyconvertor.asmx?WSDL'
        url = 'https://cotizaciones.bcu.gub.uy/wscotizaciones/servlet/awsbcucotizaciones?wsdl'
        self.ensure_connection(url=url, msg_attr = 'Servicio: Prueba > ConversionRate')
        # self.client = url
        _request = self._prepare_request_get_prueba(post_data)
        #Se obtiene resultados del servicio pubilcado, en este caso se llama ConversionRate

        #return self.client.service.ConversionRate(**_request)
        return self.client.service.Execute(_request)

        # response = False
        # try:
        #     #post_data = self.bind_method(model, cr, uid, ids, context=context)
        #     if not isinstance(post_data, (dict,)):
        #         raise Exception("Se espera un diccionario como valor de retorno. Se ha recibido el tipo: %s" % (type(post_data),))
        #     url = 'http://www.webservicex.com/currencyconvertor.asmx?WSDL'
        #     self.client = url
        #     _request = self._prepare_request_get_prueba(post_data)
        #     #Se obtiene resultados del servicio pubilcado, en este caso se llama ConversionRate
        #     response = self.client.service.ConversionRate(**_request)
        # except WebFault, e:
        #     if self.trigger_error:
        #         raise ValidationError("Error %s: %s" % (e, WebFault))
        # except Exception, e:
        #     if self.trigger_error:
        #         raise ValidationError("Error: %s" % (e.message,))
        # #Check response parameter
        # return self.execute_response(model, cr, uid, ids, response, context=context)
        # #Es lo mismo que arriba
        # # if self.bind_response and isinstance(self.bind_response,(str,)):
        # #     _resp_callback = getattr(model,self.bind_response)(cr, uid, ids, response, context=context)
        # #     if _resp_callback:
        # #         response = _resp_callback
        # # return response