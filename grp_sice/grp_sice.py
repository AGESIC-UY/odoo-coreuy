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

from base import SoapClientRequest
from grp_sice_prueba import SoapSicePrueba
from grp_sice_compra import SoapSiceCompra
from grp_sice_adjudicacion import SoapSiceAdjudicacion
from grp_sice_ampliacion import SoapSiceAmpliacion
from grp_sice_orden_compra import SoapSiceOrdenCompra
from grp_sice_factura import SoapSiceFactura
from grp_sice_factura_ajuste import SoapSiceFacturaAjuste

#Web service registry
#Test
SoapClientRequest.register('prueba', SoapSicePrueba)
#Compra
SoapClientRequest.register('compra', SoapSiceCompra)
#Adjudicación
SoapClientRequest.register('adjudicacion', SoapSiceAdjudicacion)
#Ampliacion
SoapClientRequest.register('ampliacion', SoapSiceAmpliacion)
#Orden Compra
SoapClientRequest.register('orden_compra', SoapSiceOrdenCompra)
#Factura
SoapClientRequest.register('factura', SoapSiceFactura)
#Factura Ajuste
SoapClientRequest.register('factura_ajuste', SoapSiceFacturaAjuste)

#Start Point
soap_sice = SoapClientRequest()