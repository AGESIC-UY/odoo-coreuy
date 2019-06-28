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

import logging

_logger = logging.getLogger(__name__)

from openerp.osv import osv, orm, fields
import re
import string
from openerp import netsvc
import datetime
import time
import openerp.addons.decimal_precision as dp
from openerp.tools import ustr
from openerp import pooler
from openerp.osv.orm import browse_record, browse_null
from openerp.tools.translate import _
from collections import defaultdict
from openerp import SUPERUSER_ID, api
from openerp.tools.sql import drop_view_if_exists
from openerp import tools
from datetime import date, datetime
from openerp import models
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP


class grp_solicitud_compra(osv.osv):
    _inherit = ['mail.thread']
    _name = 'grp.solicitud.compra'
    _description = 'Solicitud de compra'
    _order = 'id desc'

    def create(self, cr, uid, values, context=None):
        if context is None:
            context = {}
        context = dict(context)
        fiscalyear_obj = self.pool.get('account.fiscalyear')
        fecha = values.get('fecha_sc',time.strftime('%Y-%m-%d'))
        uid_company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
        fiscal_year_id = fiscalyear_obj.search(cr, uid,
                                               [('date_start', '<=', fecha), ('date_stop', '>=', fecha),
                                                ('company_id', '=', uid_company_id)], context=context)
        fiscal_year_id = fiscal_year_id and fiscal_year_id[0] or False
        context.update({'fiscalyear_id': fiscal_year_id})
        sequence = self.pool.get('ir.sequence').get(cr, uid, 'solicitud.compra.number', context=context)
        ind= sequence.index('-') +1
        inciso = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.inciso
        values['name'] =  sequence[0:ind] +inciso + sequence[ind:len(sequence)]
        return super(grp_solicitud_compra, self).create(cr, uid, values, context=context)

    def _get_monto(self, cr, uid, ids, name, args, context=None):
        res = {}
        lines = self.browse(cr, uid, ids, context)
        if isinstance(lines, list):
            for line in lines:
                res[line.id] = line.cantidad_solicitada * line.precio_estimado
        else:
            res[lines.id] = lines.cantidad_solicitada * lines.precio_estimado
        return res

    def _get_solicitud_recursos(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for sc in self.browse(cr, uid, ids, context=context):
            if sc.linea_solicitud_recursos_id and sc.linea_solicitud_recursos_id.grp_id:
                id_solicitud_recursos = sc.linea_solicitud_recursos_id.grp_id.id
                sr_id = self.pool.get('grp.compras.solicitud.recursos.almacen').search(cr, uid, [
                    ('sr_id', '=', id_solicitud_recursos)], context=context)
                # PCARBALLO : Chequeo si el search devuelve una lista o no
                if len(sr_id) > 0:
                    sr_id = sr_id[0]
                res[sc.id] = sr_id
            else:
                res[sc.id] = False
        return res

    def _get_in_pedido_compra(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for sc in self.browse(cr, uid, ids, context=context):
            cr.execute("SELECT count(*) FROM grp_pedido_compra pc, "
                       "grp_linea_pedido_compra lpc, grp_solicitud_compra sc "
                       "WHERE (lpc.pedido_compra_id = pc.id) "
                       "AND (lpc.solicitud_compra_id = sc.id) "
                       "AND (pc.state not in ('cancelado','cancelado_sice')) AND sc.id=%s", (sc.id,))
            cant = cr.fetchone()[0] or 0
            res[sc.id] = cant
        return res

    def _search_pedido_compra(self, cr, uid, obj, name, args, context):
        if not args:
            return []
        cr.execute("select sc2.id id, (SELECT count(*) FROM grp_pedido_compra pc, grp_linea_pedido_compra lpc, "
                   "grp_solicitud_compra sc where lpc.pedido_compra_id = pc.id "
                   "and lpc.solicitud_compra_id = sc.id and pc.state <> 'cancelado' and sc.id = sc2.id) "
                   "from  grp_solicitud_compra sc2 where (SELECT count(*) FROM grp_pedido_compra pc, "
                   "grp_linea_pedido_compra lpc, grp_solicitud_compra sc where lpc.pedido_compra_id = pc.id "
                   "and lpc.solicitud_compra_id = sc.id and pc.state <> 'cancelado' and sc.id = sc2.id) " + str(
            args[0][1]) + str(args[0][2]))
        res = cr.fetchall()
        ids = [('id', 'in', map(lambda x: x[0], res))]
        return ids

    def _es_servicio(self, cr, uid, ids, name, args, context=None):
        res = {}
        for rec in self.browse(cr, uid, ids, context=context):
            if rec.sudo().solicitud_recursos_id.tipo_sr in ['S']:
                res[rec.id] = True
            else:
                res[rec.id] = False
        return res

    def get_solicitud_recursos_doc(self, cr, uid, ids, name, args, context=None):
        res = {}
        scs = self.browse(cr, SUPERUSER_ID, ids, context)
        for sc in scs:
            res[sc.id] = sc.solicitud_recursos_id.name or sc.solicitud_recursos_id.sr_id.name
        return res

    def _get_uom(self, cr, uid, ids, name, args, context=None):
        res = {}
        for sc in self.browse(cr, SUPERUSER_ID, ids, context):
            res[sc.id] = sc.uom_id_fixed or \
                        (sc.product_id and sc.product_id.uom_id and sc.product_id.uom_id.id or False)
        return res

    LISTA_ESTADOS = [
        ('open', 'Abierto'),
        ('cancel', u'Cancelada'),
    ]

    _columns = {
        'linea_solicitud_recursos_id': fields.many2one('grp.compras.solicitud.recursos.line.sr', u'Línea asociada',
                                                       ondelete='restrict', readonly=True),
        'product_id': fields.many2one('product.product', 'Producto'),  # readonly=True),
        'pedido_compra_id': fields.many2one('grp.pedido.compra', 'Pedido asociado', readonly=True),
        'company_id': fields.many2one('res.company', u'Compañía', readonly=True, required=True),
        'solicitud_recursos_id': fields.function(_get_solicitud_recursos, type='many2one',
                                                 relation='grp.compras.solicitud.recursos.almacen',
                                                 string='Documento de Origen', store=True),
        'solicitud_recursos_doc': fields.function(get_solicitud_recursos_doc, type='char', store=True,
                                                  string=u'Solicitud de Recursos', help=u'Documento de Origen'),

        'department_id': fields.many2one('hr.department', u'Departamento', readonly=True),
        #'uom_id': fields.related('product_id', 'uom_id', type='many2one', relation='product.uom', string='UdM',
        #                         readonly=True),
        'uom_id': fields.function(_get_uom, type='many2one', relation='product.uom', string='UdM',
                                 readonly=True),
        'uom_id_fixed': fields.integer('UdM fija', readonly=True), # UoM ID fixed not relational
        'odg': fields.related('product_id', 'grp_objeto_del_gasto', 'Estado', type='integer', readonly=True),
        'almacen': fields.related('solicitud_recursos_id', 'warehouse', string=u'Almacén', readonly=True,
                                  type='many2one', relation='stock.warehouse'),
        'name': fields.char(u'Nro. de solicitud', readonly=True),
        'fecha_sc': fields.date(u'Fecha de creación', readonly=True),
        'cantidad_solicitada': fields.float('Cantidad solicitada'),  # readonly=True),
        'precio_estimado': fields.float('Precio unitario estimado', digits_compute=dp.get_precision('Cantidad'),
                                        required=True, readonly=True),

        'description': fields.text(u'Descripción', size=50, readonly=True),  # Descripcion
        'monto': fields.function(_get_monto, type='float', digits_compute=dp.get_precision('Cantidad'),
                                 string='Monto total'),
        'solicitante_id': fields.many2one('res.users', 'Solicitante', readonly=True),
        'origen': fields.char(u'Origen'),
        'inciso': fields.char('Inciso', size=02),
        'u_e': fields.char('Unidad Ejecutora', size=03),
        'en_pedido_compra': fields.function(_get_in_pedido_compra, type='integer', string=u'En línea de pedido compras',
                                            fnct_search=_search_pedido_compra),  # nuevo campo
        'es_servicio': fields.function(_es_servicio, type="boolean", string=u"Es un servicio?"),
        'state': fields.selection(LISTA_ESTADOS, 'Estado', size=20, track_visibility='onchange'),
    }

    ###################################################
    ### FUNCIÓN QUE CREA LAS SC A PARTIR DE LAS SR ####
    ###################################################
    def do_merge_sr(self, cr, uid, ids, context=None):
        '''
            En 'ids' recibimos los identificadores de las solicitudes de recurso
            que compondran los nuevos solicitudes de compra.

        '''
        solicitud_data = {}
        # Datos necesarios para crear el nuevo pedido de compra
        solicitud_data['linea_de_solicitud_compra'] = [(6, 0, ids), ]
        # Crear el nuevo pedido de compra con los ids de las solicitudes de compra que se seleccionaron
        solicitud_obj = self.pool.get('grp.solicitud.compra')
        x = solicitud_obj.create(cr, uid, solicitud_data, context=context)
        return x

    _defaults = {
        'fecha_sc': fields.date.context_today,
        'state': 'open',
    }

    def _prepare_crear_solicitud_linea(self, cr, uid, browse_id, context=None):
        if not context:
            context = {}
        res_sc = {
            'product_id': browse_id.product_id.id,
            'cantidad_solicitada': context.get('es_wizard',
                                               False) and browse_id.cantidad_pedida or browse_id.cantidad_solicitada,
            'linea_solicitud_recursos_id': browse_id.id,
            'solicitante_id': browse_id.grp_id.solicitante_id and browse_id.grp_id.solicitante_id.id or uid,
            # incidencia 19-02
            'company_id': self.pool.get('res.company')._company_default_get(cr, uid, 'product.template',
                                                                            context=context),
            'precio_estimado': browse_id.product_id.standard_price,
            'description': browse_id.descripcion,
            'inciso': browse_id.grp_id.inciso,
            'u_e': browse_id.grp_id.u_e,
            'origen': browse_id.grp_id.department_id.name,
            'department_id': browse_id.grp_id.department_id.id,
            # le asigno unidad de medida a la SC desde la linea de la SR
            'uom_id_fixed': browse_id.uom_id.id,
        }
        return res_sc

    def _crear_solicitud_linea(self, cr, uid, browse_id, context=None):
        if not context:
            context = {}
        sc_id = self.pool.get('grp.solicitud.compra').create(cr, uid, self._prepare_crear_solicitud_linea(cr, uid, browse_id, context=context))
        return sc_id

    def anular_sc(self, cr, uid, ids, context=None):
        lines_pool = self.pool.get('grp.compras.solicitud.recursos.line.sr')
        for sc in self.browse(cr, uid, ids, context=context):
            if sc.linea_solicitud_recursos_id:
                lines_pool.write(cr, uid, [sc.linea_solicitud_recursos_id.id], {'cantidad_en_pedido': sc.linea_solicitud_recursos_id.cantidad_en_pedido - sc.cantidad_solicitada})
        self.write(cr, uid, ids, {'state': 'cancel'})
        return True

    def unlink(self, cr, uid, ids, context=None):
        lines_pool = self.pool.get('grp.compras.solicitud.recursos.line.sr')
        for sc in self.browse(cr, uid, ids, context=context):
            if sc.state != 'cancel' and sc.linea_solicitud_recursos_id and sc.cantidad_solicitada:
                lines_pool.write(cr, uid, [sc.linea_solicitud_recursos_id.id], {'cantidad_en_pedido': sc.linea_solicitud_recursos_id.cantidad_en_pedido - sc.cantidad_solicitada})
        return super(grp_solicitud_compra, self).unlink(cr, uid, ids, context=context)
