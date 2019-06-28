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

from suds.client import Client
from suds.cache import NoCache
from suds import WebFault
from openerp.exceptions import ValidationError

class SoapClientRequest(object):
    """ Web Service Client Request """
    _register = {}

    def __getattr__(self, name):
        return self._register[name]

    @classmethod
    def register(cls, key, classvalue):
        if isinstance(key,(list,)):
            for i in key:
                cls._register[i] = classvalue
        else:
            cls._register[key] = classvalue

class SoapClientBase(object):
    """ Web Service Client Base """

    def __init__(self, request, response=False, trigger_error=True, new_api=False):
        self.request = request
        self.bind_method = None
        self.trigger_error = trigger_error
        self.bind_response = response
        self.new_api = new_api
        self._client = None

    def __call__(self, m):
        self.bind_method = m
        #Parse REQUEST_SERVICE
        return self.__attrs_request_service()

    #---- Propiedad client encargada de la comunicación SOAP. Sola es necesario asignarle la URL
    @property
    def client(self):
        return self._client
    @client.setter
    def client(self, value):
        if isinstance(value,(str, unicode)):
            self._client = Client(value, cache=NoCache())
        else:
            self._client = value
    @client.deleter
    def client(self):
        del self._client
    #--------------------------------------------------------------------------------------------

    def __aspect_request(self, fnt):
        def _old_api(model, cr, uid, ids, post_data, context=None):
            response = False
            try:
                response = fnt(model, cr, uid, ids, post_data, context=context)
            except WebFault, e:
                if self.trigger_error:
                    raise ValidationError("Error: %s" % (e.fault,))
            except Exception, e:
                if self.trigger_error:
                    raise ValidationError("Error: %s" % (e.message,))
            #Check response parameter
            return self.execute_response(model, cr, uid, ids, response, context=context)
        def _new_api(model, post_data):
            response = False
            try:
                response = fnt(model, post_data)
            except WebFault, e:
                if self.trigger_error:
                    raise ValidationError("Error: %s" % (e.fault,))
            except Exception, e:
                if self.trigger_error:
                    raise ValidationError("Error: %s" % (e.message,))
            #Check response parameter
            return self.execute_response_api(model, response)
        return self.new_api and _new_api or _old_api

    def __attrs_request_service(self):
        if hasattr(self, 'request_'+self.request):
            if self.new_api:
                return lambda model: self.__aspect_request(getattr(self, 'request_'+self.request))(model, self.bind_method(model) or False)
            return lambda model, cr, uid, ids, context=None: self.__aspect_request(getattr(self, 'request_'+self.request))(model, cr, uid, ids, self.bind_method(model, cr, uid, ids, context=context) or False, context=context)
        raise Exception(u"No se encuentra la función %s" % ('request_'+self.request,))

    def execute_response(self, model, cr, uid, ids, response, context=None):
        if self.bind_response and isinstance(self.bind_response,(str,)):
            _resp_callback = getattr(model,self.bind_response)(cr, uid, ids, response, context=context)
            if _resp_callback:
                response = _resp_callback
        return response

    def execute_response_api(self, model, response):
        if self.bind_response and isinstance(self.bind_response,(str,)):
            _resp_callback = getattr(model,self.bind_response)(response)
            if _resp_callback:
                response = _resp_callback
        return response

    def ensure_connection(self, url="", msg_attr=""):
        try:
            if url:
                self.client = url
        except:
            msg = u"Imposible conectarse al Servicio Web seleccionado, verifique la URL y datos de conexión."
            if msg:
                msg += "\n %s" % (msg_attr,)
            raise Exception(msg)

class Dic2Object(dict):
    def __init__(self, *args, **kwargs):
        super(Dic2Object, self).__init__(*args, **kwargs)
        self.__dict__ = self