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

from openerp.osv import osv, fields, orm
import openerp.addons.decimal_precision as dp
from openerp.tools.sql import drop_view_if_exists
from openerp import netsvc, api, SUPERUSER_ID, exceptions
from openerp.tools.translate import _
import time, datetime
from lxml import etree
from openerp.osv.orm import setup_modifiers

class grp_compras_stock_picking(osv.osv):
    _inherit = 'stock.picking'

    def _state_get(self, cr, uid, ids, field_name, arg, context=None):
        '''The state of a picking depends on the state of its related stock.move
            draft: the picking has no line or any one of the lines is draft
            done, draft, cancel: all lines are done / draft / cancel
            confirmed, waiting, assigned, partially_available depends on move_type (all at once or partial)
        '''
        res = {}
        for pick in self.browse(cr, uid, ids, context=context):
            #MVARELA: Se agrega estado approve
            if (not pick.move_lines) or any([x.state in ['draft','to_approve','approved'] for x in pick.move_lines]):
                res[pick.id] = 'draft'
                continue
            if all([x.state == 'cancel' for x in pick.move_lines]):
                res[pick.id] = 'cancel'
                continue
            if all([x.state in ('cancel', 'done') for x in pick.move_lines]):
                res[pick.id] = 'done'
                continue

            order = {'confirmed': 0, 'waiting': 1, 'assigned': 2}
            order_inv = {0: 'confirmed', 1: 'waiting', 2: 'assigned'}
            lst = [order[x.state] for x in pick.move_lines if x.state not in ('cancel', 'done')]
            if pick.move_type == 'one':
                res[pick.id] = order_inv[min(lst)]
            else:
                # we are in the case of partial delivery, so if all move are assigned, picking
                # should be assign too, else if one of the move is assigned, or partially available, picking should be
                # in partially available state, otherwise, picking is in waiting or confirmed state
                res[pick.id] = order_inv[max(lst)]
                if not all(x == 2 for x in lst):
                    if any(x == 2 for x in lst):
                        res[pick.id] = 'partially_available'
                    else:
                        # if all moves aren't assigned, check if we have one product partially available
                        for move in pick.move_lines:
                            if move.partially_available:
                                res[pick.id] = 'partially_available'
                                break
        return res

    def _get_pickings(self, cr, uid, ids, context=None):
        res = set()
        for move in self.browse(cr, uid, ids, context=context):
            if move.picking_id:
                res.add(move.picking_id.id)
        return list(res)

    def create(self, cr, uid, vals, context=None):
        _r = super(grp_compras_stock_picking, self).create(cr, uid, vals, context=context)
        row = self.browse(cr, uid, _r, context=context)
        move_ids = []
        for move in row.move_lines:
            if row.location_id.id != move.location_id.id or row.location_dest_id.id != move.location_dest_id.id or row.picking_type_id.id != (move.picking_type_id and move.picking_type_id.id or False):
                move_ids.append(move.id)
        if move_ids:
            self.pool.get('stock.move').write(cr, uid, move_ids, {
                                                                    'picking_type_id': row.picking_type_id.id,
                                                                    'location_id': row.location_id.id,
                                                                    'location_dest_id': row.location_dest_id.id
                                                                }, context=context)
        return _r

    def write(self, cr, uid, ids, vals, context=None):
        _r = super(grp_compras_stock_picking, self).write(cr, uid, ids, vals, context=context)
        for row in self.browse(cr, uid, ids, context=context):
            move_ids = []
            for move in row.move_lines:
                if row.location_id.id != move.location_id.id or row.location_dest_id.id != move.location_dest_id.id or row.picking_type_id.id != (move.picking_type_id and move.picking_type_id.id or False):
                    move_ids.append(move.id)
            if move_ids:
                self.pool.get('stock.move').write(cr, uid, move_ids, {
                                                                        'picking_type_id': row.picking_type_id.id,
                                                                        'location_id': row.location_id.id,
                                                                        'location_dest_id': row.location_dest_id.id
                                                                    }, context=context)
            if row.pack_operation_ids and row.state in ['assigned','partially_available']and (('picking_type_id' in vals) or ('location_id' in vals) or ('location_dest_id' in vals)):
                self.recheck_availability(cr, uid, [row.id], context=context)
        return _r

    @api.onchange('picking_type_id')
    def onchange_picking_type_id(self):
        if self.picking_type_id:
            prod_obj = self.env['product.product']
            wh_obj = self.env['stock.warehouse']
            loc_obj = self.env['stock.location']
            #Se verifica que los valores no vengan por context (Ej: desde solicitud de recursos y orden de compra)
            self.location_id = self._context.get('default_location_id', False)
            self.location_dest_id = self._context.get('default_location_dest_id', False)
            if self.picking_type_id.code == 'internal':
                if self.picking_type_id.warehouse_id:
                    #El location_dest_id debe ser todas los locations válidos para los almacenes donde el usuario autenticado esté
                    #en la lista de encargados. En el caso de SUPERUSER tiene todos los privilegios
                    # loc_dest_domain = [('usage','!=','view')]
                    loc_dest_domain = []
                    if self._uid != SUPERUSER_ID:
                        _loc_dest_ids = []
                        for wh in wh_obj.search([('encargado_ids.id','=',self._uid)]):
                            # _loc_domain_dest_ids = [('usage','!=','view')]
                            _loc_domain_dest_ids = []
                            domains = prod_obj.with_context({
                                'warehouse': wh.id,
                                'compute_child': True
                            })._get_domain_locations()
                            if domains:
                                for _d in domains[0]:
                                    if not isinstance(_d,(tuple,)):
                                        _loc_domain_dest_ids.append(_d)
                                    else:
                                        _loc_domain_dest_ids.append(('parent_left',_d[1],_d[2]))
                                _loc_dest_ids += loc_obj.search(_loc_domain_dest_ids).ids
                        loc_dest_domain.append(('id','in',_loc_dest_ids))
                    #El location_id es el dominio de los locations válidos para el almacén configurado en stok.picking.type
                    loc_domain = [('usage','!=','view')]
                    domains = prod_obj.with_context({
                        'warehouse': self.picking_type_id.warehouse_id.id,
                        'compute_child': True
                    })._get_domain_locations()
                    if domains:
                        for _d in domains[0]:
                            if not isinstance(_d,(tuple,)):
                                loc_domain.append(_d)
                            else:
                                loc_domain.append(('parent_left',_d[1],_d[2]))
                    return {
                        'domain': {
                            'location_id': loc_domain,
                            'location_dest_id': loc_dest_domain
                        }
                    }
                else:
                    return {
                        'domain': {'location_id': [('id', '=', False)], 'location_dest_id': [('id', '=', False)]},
                        'warning': {'title': "Error", 'message': u"El tipo de tranferencia no tiene configurado ningún almacén"},
                    }
            else:
                #Se valida desde la interfaz de stock.picking para los casos de stock.picking.type outgoing y incoming
                #Salida
                if self.picking_type_id.code == 'outgoing':
                    _dest_id = self._context.get('default_location_dest_id', False)
                    if not _dest_id:
                        _dest_id = self.picking_type_id.default_location_dest_id and self.picking_type_id.default_location_dest_id.id or False
                    self.location_dest_id = _dest_id
                    loc_domain = [('usage','!=','view')]
                    domains = prod_obj.with_context({
                        'warehouse': self.picking_type_id.warehouse_id.id,
                        'compute_child': True
                    })._get_domain_locations()
                    if domains:
                        for _d in domains[0]:
                            if not isinstance(_d,(tuple,)):
                                loc_domain.append(_d)
                            else:
                                loc_domain.append(('parent_left',_d[1],_d[2]))
                    #El location_id es el dominio de los locations válidos para el almacén configurado en stok.picking.type
                    #El location_dest_id es el location de destino por defecto configurado en stock.picking.type (default_location_dest_id)
                    return {
                        'domain': {'location_id': loc_domain, 'location_dest_id': [('id','in',[_dest_id])]}
                    }
                #Recepciones
                if self.picking_type_id.code == 'incoming':
                    _src_id = self._context.get('default_location_id', False)
                    if not _src_id:
                        _src_id = self.picking_type_id.default_location_src_id.id and self.picking_type_id.default_location_src_id.id or False
                    self.location_id = _src_id
                    # loc_dest_domain = [('usage','!=','view')]
                    loc_dest_domain = []
                    domains = prod_obj.with_context({
                        'warehouse': self.picking_type_id.warehouse_id.id,
                        'compute_child': True
                    })._get_domain_locations()
                    if domains:
                        for _d in domains[0]:
                            if not isinstance(_d,(tuple,)):
                                loc_dest_domain.append(_d)
                            else:
                                loc_dest_domain.append(('parent_left',_d[1],_d[2]))
                    #El location_id es el location de destino por defecto configurado en stock.picking.type (default_location_src_id)
                    #El location_dest_id es el dominio de los locations válidos para el almacén configurado en stok.picking.type
                    return {
                        'domain': {'location_id': [('usage','!=','view'),('id','in',[_src_id])], 'location_dest_id': loc_dest_domain}
                    }
        else:
            self.location_id = False
            self.location_dest_id = False
        return {
            'domain': {'location_id': [('usage','!=','view')], 'location_dest_id': []}
        }

    _columns = {
        'location_id': fields.many2one('stock.location', u'Ubicación origen', required=True, select=True, auto_join=True,
                                       states={'done': [('readonly', True)], 'cancel': [('readonly', True)]}),
        'location_dest_id': fields.many2one('stock.location', 'Destination Location', required=True, states={'done': [('readonly', True)], 'cancel': [('readonly', True)]}, select=True, auto_join=True),
        'fecha_prev': fields.datetime('Fecha prevista'),
        'warehouse': fields.many2one('stock.warehouse', u'Almacén'),
        'solicitante_id': fields.many2one('res.users', 'Solicitante', readonly=True),
        'department_id': fields.many2one('hr.department', string='Oficina', readonly=True),
        'doc_origin': fields.many2one('grp.compras.solicitud.recursos.almacen', 'Documento origen'),
        # TODO GAP 247 Spring 4: Agregando la fecha de asiento y el many2one con asiento definir bien si es un many2one por que son varios asientos
        # todo ponerle el required en el view para que no explote por los datos que tiene ya
        'account_move_date': fields.date('Fecha asiento', states={'done': [('readonly', True)]}, select=True),
        'state': fields.function(_state_get, type="selection", copy=False,
                                 store={
                                     'stock.picking': (lambda self, cr, uid, ids, ctx: ids, ['move_type'], 20),
                                     'stock.move': (_get_pickings, ['state', 'picking_id', 'partially_available'], 20)},
                                 selection=[
                                     ('draft', 'Draft'),
                                     ('cancel', 'Cancelled'),
                                     ('waiting', 'Waiting Another Operation'),
                                     ('confirmed', 'Waiting Availability'),
                                     ('partially_available', 'Partially Available'),
                                     ('assigned', 'Ready to Transfer'),
                                     ('done', 'Transferred'),
                                 ], string='Status', readonly=True, select=True, track_visibility='onchange',
                                 help="""
            * Draft: not confirmed yet and will not be scheduled until confirmed\n
            * Waiting Another Operation: waiting for another move to proceed before it becomes automatically available (e.g. in Make-To-Order flows)\n
            * Waiting Availability: still waiting for the availability of products\n
            * Partially Available: some products are available and reserved\n
            * Ready to Transfer: products reserved, simply waiting for confirmation.\n
            * Transferred: has been processed, can't be modified or cancelled anymore\n
            * Cancelled: has been cancelled, can't be confirmed anymore"""
                                 )
    }

    _defaults = {
        'solicitante_id': lambda s, cr, uid, c: uid,
        'department_id': lambda s, cr, uid, c: c.get('department_id', False) if c and 'department_id' in c else s.pool.get(
            'res.users').get_departamento(cr, uid, uid),
    }

    def _prepare_invoice_line(self, cr, uid, group, picking, move_line, invoice_id, invoice_vals, context=None):
        valores = super(grp_compras_stock_picking, self)._prepare_invoice_line(cr, uid, group, picking, move_line, invoice_id,
                                                                       invoice_vals, context=context)
        valores['orden_compra_id'] = picking.purchase_id.id
        return valores

    # TODO GAP 247 Spring 4
    @api.cr_uid_ids_context
    def do_transfer(self, cr, uid, picking_ids, context=None):
        """
            Redefiniendo el metodo para q los stock.moves tengas la fecha de asiento que se configuro en el stock.picking
        """
        for picking in self.browse(cr, uid, picking_ids, context=context):
            if picking.account_move_date:
                for move in picking.move_lines:
                    if move.state != 'done':
                        move.write({'account_move_date': picking.account_move_date})
        super(grp_compras_stock_picking, self).do_transfer(cr, uid, picking_ids, context=context)

    # TODO GAP 3 Spring 4: Verificando el usuario que realiza la transferencia
    @api.cr_uid_ids_context
    def do_enter_transfer_details(self, cr, uid, picking, context=None):
        pick = self.browse(cr, uid, picking[0], context=context)
        if picking and uid not in pick.picking_type_id.warehouse_id.encargado_ids.ids:
            tipo_ubicacion = 'origen'
            if pick.picking_type_id.code == 'incoming':
                tipo_ubicacion = "destino"
            raise osv.except_osv(_('Warning!'), _(u'Usted no es encargado del almacén de la ubicación %s, no podrá realizar la transferencia.') % (tipo_ubicacion,))
        return super(grp_compras_stock_picking, self).do_enter_transfer_details(cr, uid, picking, context=context)

    def action_assign(self, cr, uid, ids, context=None):
        """ Se verifica que el usuario sea responsable del almacen origen
        """
        for picking in self.browse(cr, uid, ids, context=context):
            tipo_ubicacion = 'origen'
            if picking.picking_type_id.code == 'incoming':
                tipo_ubicacion = "destino"
            if uid not in picking.picking_type_id.warehouse_id.encargado_ids.ids:
                raise osv.except_osv(_('Warning!'), _(u'Usted no es encargado del almacén de la ubicación %s, no podrá realizar la transferencia.') % (tipo_ubicacion,))
        return super(grp_compras_stock_picking, self).action_assign(cr, uid, ids, context=context)


    def force_assign(self, cr, uid, ids, context=None):
        """ Se verifica que el usuario sea responsable del almacen origen
        """
        for picking in self.browse(cr, uid, ids, context=context):
            tipo_ubicacion = 'origen'
            if picking.picking_type_id.code == 'incoming':
                tipo_ubicacion = "destino"
            if uid not in picking.picking_type_id.warehouse_id.encargado_ids.ids:
                raise osv.except_osv(_('Warning!'), _(
                    u'Usted no es encargado del almacén de la ubicación %s, no podrá realizar la transferencia.') % (tipo_ubicacion,))
        return super(grp_compras_stock_picking, self).force_assign(cr, uid, ids, context=context)


    def action_confirm(self, cr, uid, ids, context=None):
        """ Se verifica que el usuario sea responsable del almacen origen
        """
        for picking in self.browse(cr, uid, ids, context=context):
            tipo_ubicacion = 'destino'
            if picking.picking_type_id.code == 'outgoing':
                tipo_ubicacion = "origen"
            if picking.picking_type_id.code == 'internal':
                almacen_id = self.pool.get("stock.location").get_warehouse(cr, uid, picking.location_dest_id, context=context)
                if not almacen_id:
                    raise osv.except_osv(_('Warning!'), _(u'No se pudo obtener el almacen a partir de la ubicación destino.'))
                almacen = self.pool.get("stock.warehouse").browse(cr, uid, almacen_id, context=context)

            else:
                almacen = picking.picking_type_id.warehouse_id
            if uid not in almacen.encargado_ids.ids and not picking.backorder_id:
                raise osv.except_osv(_('Warning!'), _(u'Usted no es encargado del almacén de la ubicación %s, no podrá realizar la transferencia.') % (tipo_ubicacion,))
        return super(grp_compras_stock_picking, self).action_confirm(cr, uid, ids, context=context)

class grp_stock_location(osv.osv):
    _inherit = 'stock.location'

    _columns = {
        'responsable_id': fields.many2one('res.users', 'Responsable'),
    }

# para el reporte de lineas de picking
class stock_picking_list_report(osv.osv):
    _name = "stock.picking.list.report"
    _description = "Listado de remitos"
    _order = "id desc"
    _auto = False
    _rec_name = 'name'

    def _get_ubicacion_origen(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for rec in self.browse(cr, uid, ids, context=context):
            res[rec.id] = rec.picking_id.location_id.id
        return res

    def _get_ubicacion_dest(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for rec in self.browse(cr, uid, ids, context=context):
            res[rec.id] = rec.picking_id.location_dest_id.id
        return res

    _columns = {
        'id': fields.integer('Id', readonly=True),
        'picking_id': fields.many2one('stock.picking', 'Remito', required=True, select=True),
        'product_id': fields.many2one('product.product', 'Producto', required=True, select=True,
                                      domain=[('type', '<>', 'service'),('no_inventory','=',False)], states={'done': [('readonly', True)]}),
        'product_qty': fields.float('Cantidad solicitada', digits_compute=dp.get_precision('Product Unit of Measure')),
        'product_uom': fields.many2one('product.uom', 'Unidad de medida', required=True,
                                       states={'done': [('readonly', True)]}),
        'product_uos_qty': fields.float('Quantity (UOS)', digits_compute=dp.get_precision('Product Unit of Measure'),
                                        states={'done': [('readonly', True)]}),
        'state': fields.selection([('draft', 'Nuevo'),
                                   ('cancel', 'Cancelado'),
                                   ('waiting', 'Esperando otro movimiento'),
                                   ('confirmed', 'Esperando disponibilidad'),
                                   ('assigned', 'Reservado'),
                                   ('done', 'Realizado'),
                                   ], 'Estado', readonly=True, select=True),
        'name': fields.char('Referencia', size=64, select=True,
                            states={'done': [('readonly', True)], 'cancel': [('readonly', True)]}),
        'date': fields.datetime('Fecha', help="Fecha de creación, usualmente la fecha del pedido.", select=True,
                                states={'done': [('readonly', True)], 'cancel': [('readonly', True)]}),
        'department_id': fields.many2one('hr.department', string='Oficina'),
        'partner_id': fields.many2one('res.partner', 'Empresa',
                                      states={'done': [('readonly', True)], 'cancel': [('readonly', True)]}),

        'ubicacion_origen': fields.function(_get_ubicacion_origen, method=True,
                                            type='many2one', relation='stock.location', string=u'Ubicación origen'),
        'ubicacion_destino': fields.function(_get_ubicacion_dest, method=True,
                                            type='many2one', relation='stock.location', string=u'Ubicación destino'),
    }

    def init(self, cr):
        drop_view_if_exists(cr, 'stock_picking_list_report')
        cr.execute("""
         create or replace view stock_picking_list_report as (
              SELECT sm.id as id, sm.picking_id, sm.product_id, sm.product_qty, sm.product_uom, sm.product_uos_qty, sm.state,
                    p.name,
                  --p.type,
                  sm.date, p.partner_id, p.department_id
                  FROM stock_move sm inner join
                  stock_picking p on p.id = sm.picking_id)""")

class grp_almacen_lineas(osv.osv):
    _inherit = 'stock.move'

    def create(self, cr, uid, vals, context=None):
        _r = super(grp_almacen_lineas, self).create(cr, uid, vals, context=context)
        row = self.browse(cr, uid, _r, context=context)
        if row.picking_id:
            if row.origin_returned_move_id:
                if row.picking_id.location_id.id != row.location_id.id or row.picking_id.location_dest_id.id != row.location_dest_id.id or row.picking_id.picking_type_id.id != (
                        row.picking_type_id and row.picking_type_id.id or False):
                    row.picking_id.write({
                        'picking_type_id': row.picking_type_id.id,
                        'location_id': row.location_id.id,
                        'location_dest_id': row.location_dest_id.id
                    }, context=context)
            else:
                if row.picking_id.location_id.id != row.location_id.id or row.picking_id.location_dest_id.id != row.location_dest_id.id or row.picking_id.picking_type_id.id != (row.picking_type_id and row.picking_type_id.id or False):
                    row.write({
                                    'picking_type_id': row.picking_id.picking_type_id.id,
                                    'location_id': row.picking_id.location_id.id,
                                    'location_dest_id': row.picking_id.location_dest_id.id
                                }, context=context)
        return _r

    def write(self, cr, uid, ids, vals, context=None):
        _r = super(grp_almacen_lineas, self).write(cr, uid, ids, vals, context=context)
        for row in self.browse(cr, uid, ids, context=context):
            if row.picking_id and row.state != 'done':
                if row.picking_id.location_id.id != row.location_id.id or row.picking_id.location_dest_id.id != row.location_dest_id.id or row.picking_id.picking_type_id.id != (row.picking_type_id and row.picking_type_id.id or False):
                    row.write({
                                    'picking_type_id': row.picking_id.picking_type_id.id,
                                    'location_id': row.picking_id.location_id.id,
                                    'location_dest_id': row.picking_id.location_dest_id.id
                                }, context=context)
        return _r

    def onchange_product_id(self, cr, uid, ids, prod_id=False, loc_id=False, loc_dest_id=False, partner_id=False):
        if ids:
            move = self.browse(cr, uid, ids[0])
            if move.purchase_line_id:
                value = {'product_id': move.product_id.id}
                res = {'value': value}
                res['warning'] = {'title': 'Error',
                                  'message': u'No puede modificar el producto. Este remito fue generado a partir de una Orden de compra.'}
                return res
        result = super(grp_almacen_lineas, self).onchange_product_id(cr, uid, ids, prod_id=prod_id, loc_id=loc_id, loc_dest_id=loc_dest_id, partner_id=partner_id)
        if ids and result.get('value', {}) and move.line_sr_id \
           and move.line_sr_id.product_id.id != prod_id:
            product = self.pool.get('product.product').browse(cr, uid, prod_id)
            uos_id = product.uos_id and product.uos_id.id or False
            result['value'].update({
                'product_uom_qty': move.line_sr_id.cantidad_pendiente,
                'product_uos_qty': self.onchange_quantity(cr, uid, ids, prod_id, move.line_sr_id.cantidad_pendiente, product.uom_id.id, uos_id)['value']['product_uos_qty'],
            })
        return result


    @api.onchange('picking_type_id')
    def onchange_picking_type_id(self):
        if self.picking_type_id:
            prod_obj = self.env['product.product']
            wh_obj = self.env['stock.warehouse']
            loc_obj = self.env['stock.location']
            #Se verifica que los valores no vengan por context (Ej: desde solicitud de recursos y orden de compra)
            self.location_id = self._context.get('default_location_id', False)
            self.location_dest_id = self._context.get('default_location_dest_id', False)
            if self.picking_type_id.code == 'internal':
                if self.picking_type_id.warehouse_id:
                    #El location_dest_id debe ser todas los locations válidos para los almacenes donde el usuario autenticado esté
                    #en la lista de encargados. En el caso de SUPERUSER tiene todos los privilegios
                    # loc_dest_domain = [('usage','!=','view')]
                    loc_dest_domain = []
                    if self._uid != SUPERUSER_ID:
                        _loc_dest_ids = []
                        for wh in wh_obj.search([('encargado_ids.id','=',self._uid)]):
                            # _loc_domain_dest_ids = [('usage','!=','view')]
                            _loc_domain_dest_ids = []
                            domains = prod_obj.with_context({
                                'warehouse': wh.id,
                                'compute_child': True
                            })._get_domain_locations()
                            if domains:
                                for _d in domains[0]:
                                    if not isinstance(_d,(tuple,)):
                                        _loc_domain_dest_ids.append(_d)
                                    else:
                                        _loc_domain_dest_ids.append(('parent_left',_d[1],_d[2]))
                                _loc_dest_ids += loc_obj.search(_loc_domain_dest_ids).ids
                        loc_dest_domain.append(('id','in',_loc_dest_ids))
                    #El location_id es el dominio de los locations válidos para el almacén configurado en stok.picking.type
                    loc_domain = [('usage','!=','view')]
                    domains = prod_obj.with_context({
                        'warehouse': self.picking_type_id.warehouse_id.id,
                        'compute_child': True
                    })._get_domain_locations()
                    if domains:
                        for _d in domains[0]:
                            if not isinstance(_d,(tuple,)):
                                loc_domain.append(_d)
                            else:
                                loc_domain.append(('parent_left',_d[1],_d[2]))
                    return {
                        'domain': {
                            'location_id': loc_domain,
                            'location_dest_id': loc_dest_domain
                        }
                    }
                else:
                    return {
                        'domain': {'location_id': [('id', '=', False)], 'location_dest_id': [('id', '=', False)]},
                        'warning': {'title': "Error", 'message': u"El tipo de tranferencia no tiene configurado ningún almacén"},
                    }
            else:
                #Se valida desde la interfaz de stock.picking para los casos de stock.picking.type outgoing y incoming
                #Salida
                if self.picking_type_id.code == 'outgoing':
                    _dest_id = self._context.get('default_location_dest_id', False)
                    if not _dest_id:
                        _dest_id = self.picking_type_id.default_location_dest_id and self.picking_type_id.default_location_dest_id.id or False
                    self.location_dest_id = _dest_id
                    loc_domain = [('usage','!=','view')]
                    domains = prod_obj.with_context({
                        'warehouse': self.picking_type_id.warehouse_id.id,
                        'compute_child': True
                    })._get_domain_locations()
                    if domains:
                        for _d in domains[0]:
                            if not isinstance(_d,(tuple,)):
                                loc_domain.append(_d)
                            else:
                                loc_domain.append(('parent_left',_d[1],_d[2]))
                    #El location_id es el dominio de los locations válidos para el almacén configurado en stok.picking.type
                    #El location_dest_id es el location de destino por defecto configurado en stock.picking.type (default_location_dest_id)
                    return {
                        'domain': {'location_id': loc_domain, 'location_dest_id': [('id','in',[_dest_id])]}
                    }
                #Recepciones
                if self.picking_type_id.code == 'incoming':
                    _src_id = self._context.get('default_location_id', False)
                    if not _src_id:
                        _src_id = self.picking_type_id.default_location_src_id.id and self.picking_type_id.default_location_src_id.id or False
                    self.location_id = _src_id
                    # loc_dest_domain = [('usage','!=','view')]
                    loc_dest_domain = []
                    domains = prod_obj.with_context({
                        'warehouse': self.picking_type_id.warehouse_id.id,
                        'compute_child': True
                    })._get_domain_locations()
                    if domains:
                        for _d in domains[0]:
                            if not isinstance(_d,(tuple,)):
                                loc_dest_domain.append(_d)
                            else:
                                loc_dest_domain.append(('parent_left',_d[1],_d[2]))
                    #El location_id es el location de destino por defecto configurado en stock.picking.type (default_location_src_id)
                    #El location_dest_id es el dominio de los locations válidos para el almacén configurado en stok.picking.type
                    return {
                        'domain': {'location_id': [('usage','!=','view'),('id','in',[_src_id])], 'location_dest_id': loc_dest_domain}
                    }
        else:
            self.location_id = False
            self.location_dest_id = False
        return {
            'domain': {'location_id': [('usage','!=','view')], 'location_dest_id': []}
        }

    # TODO GAP 3 Spring 4:
    def is_warehouse_attendant(self, cr, uid, ids, stock_move, context=None):
        warehouse = self.pool.get('stock.warehouse').search(cr, uid, [('encargado_ids', '=', uid)], context=context)
        if stock_move.picking_type_id.warehouse_id.id in warehouse:
            return True
        return False

    def is_origin_location_attendant(self, cr, uid, ids, stock_move, context=None):
        parent_location = stock_move.location_id.location_id.name
        warehouse_ids = self.pool.get('stock.warehouse').search(cr, uid,
            [('code', '=', parent_location), ('encargado_ids', '=', uid)], context=context)
        return len(warehouse_ids)

    def is_destiny_location_attendant(self, cr, uid, ids, stock_move, context=None):
        parent_location = stock_move.location_dest_id.location_id.name
        warehouse_ids = self.pool.get('stock.warehouse').search(cr, uid,
            [('code', '=', parent_location), ('encargado_ids', '=', uid)], context=context)
        return len(warehouse_ids)

    def _compute_allow_edit(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for rec in self.browse(cr, uid, ids, context=context):
            if not rec.is_internal_transfer:
                if rec.picking_type_id.code == 'incoming':
                    res[rec.id] = self.is_destiny_location_attendant(cr, uid, ids, rec, context=context)
                else:
                    res[rec.id] = self.is_origin_location_attendant(cr, uid, ids, rec,context=context)
            else:
                if rec.state != 'to_approve':
                    res[rec.id] = self.is_origin_location_attendant(cr, uid, ids, rec, context=context)
                else:
                    res[rec.id] = self.is_destiny_location_attendant(cr, uid, ids, rec, context=context)

        return res

    def _compute_transfer_type(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for rec in self.browse(cr, uid, ids, context=context):
            res[rec.id] = True
            if rec.picking_type_id:
                res[rec.id] = rec.picking_type_id.code == 'internal'
        return res

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        res = super(grp_almacen_lineas, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type,
                                                                context=context,
                                                                toolbar=toolbar, submenu=submenu)
        user_allow = self.pool.get('res.users').has_group(cr, uid, 'grp_compras_estatales.grp_stock_move_create')

        doc = etree.XML(res['arch'])
        if view_id and view_type == 'form':
            warehouse = self.pool.get('stock.warehouse').search(cr, uid, [('encargado_ids', '=', uid)])
            picking_type = self.pool.get('stock.picking.type').search(cr, uid, [('warehouse_id', 'in', warehouse)])
            for field in res['fields']:
                node = doc.xpath("//field[@name='" + field + "']")[0]
                if field == 'picking_type_id':
                    res['fields'][field]['domain'] = [('id', 'in', picking_type)]
                #TODO: Revisar, esta pasando por arriba el attrs definido
                # if field != 'allow_edit' and field != 'id':
                #     node.set('attrs', "{'readonly': [('allow_edit', '=', False),('id', '!=', False)]}")
                setup_modifiers(node, res['fields'][field])

        res['arch'] = etree.tostring(doc)
        return res

    _columns = {
        'cantidad_solicitada': fields.float('Cantidad Solicitada',
                                            digits_compute=dp.get_precision('Cantidad Solicitada'), readonly=True),
        'solicitante_id': fields.many2one('res.users', 'Solicitante'),
        # TODO GAP 247 Spring 4: Agregando la fecha de asiento preguntar bien si los cambios deben ser aqui o en grp_sotck
        # todo ponerle el required en el view para que no explote por los datos que tiene ya
        'account_move_date': fields.date('Fecha asiento', states={'done': [('readonly', True)]}, select=True),
        'account_move_id': fields.many2one('account.move', string='Asiento', readonly=True, copy=False),

        # TODO GAP 251 Spring 4:
        'is_internal_transfer': fields.function(_compute_transfer_type, type='boolean',
                                                string='Es Tranferencia interna?'),
        'state': fields.selection([('draft', 'New'),
                              ('to_approve', u'En Aprobación'),
                              ('approved', 'Aprobado'),
                              ('cancel', 'Cancelled'),
                              ('waiting', 'Waiting Another Move'),
                              ('confirmed', 'Waiting Availability'),
                              ('assigned', 'Available'),
                              ('done', 'Done'),
                              ], 'Status', readonly=True, select=True, copy=False,
                             help="* New: When the stock move is created and not yet confirmed.\n" \
                                  "* Waiting Another Move: This state can be seen when a move is waiting for another one, for example in a chained flow.\n" \
                                  "* Waiting Availability: This state is reached when the procurement resolution is not straight forward. It may need the scheduler to run, a component to me manufactured...\n" \
                                  "* Available: When products are reserved, it is set to \'Available\'.\n" \
                                  "* Done: When the shipment is processed, the state is \'Done\'.",
                             track_visibility="onchange"),
        # TODO GAP 3 Spring 4:
        'allow_edit': fields.function(_compute_allow_edit, type='boolean', string='Permitir Editar?'),
        ## Referencia a la línea de solicitud de recursos
        'line_sr_id': fields.many2one('grp.compras.solicitud.recursos.line.sr', u'Línea SR'),
        'sr_product_uom_qty': fields.float('Cantidad SR', digits_compute=dp.get_precision('Product Unit of Measure'), states={'done': [('readonly', True)]}),
        'sr_product_uom': fields.many2one('product.uom', 'UdM SR', states={'done': [('readonly', True)]}),
        ##
        'acc_entry_currency_id': fields.many2one('res.currency', 'Moneda del asiento', readonly=True),
        'acc_entry_amount_currency': fields.float('Importe divisa del asiento', readonly=True, help="Importe divisa por unidad"),
    }

    _defaults = {
        'is_internal_transfer': True,
        'allow_edit': False,
        # TODO GAP 247 Spring 4:
        'account_move_date': lambda *a: datetime.date.today().strftime('%Y-%m-%d'),
    }

    # TODO GAP 251 Spring 4:
    def action_to_approve(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'to_approve'})

    def action_approve(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'approved'}, context=context)

    def action_reject(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'cancel'}, context=context)

    # TODO GAP 3 Spring 4:
    def unlink(self, cr, uid, ids, context=None):
        for rec in self.browse(cr, uid, ids, context=context):
            if not rec.is_internal_transfer:
                if rec.picking_type_id.code == 'incoming' and not self.is_destiny_location_attendant(cr, uid, ids, rec, context=context):
                    raise osv.except_osv(_('Warning!'), _('No puede eliminar un movimiento de existencia al cual no tiene permiso.'))
                if rec.picking_type_id.code == 'outgoing' and not self.is_origin_location_attendant(cr, uid, ids, rec, context=context):
                    raise osv.except_osv(_('Warning!'),
                                         _('No puede eliminar un movimiento de existencia al cual no tiene permiso.'))
            else:
                if rec.state != 'draft' and not self.is_destiny_location_attendant(cr, uid, ids, rec, context=context):
                    raise osv.except_osv(_('Warning!'),
                                         _('No puede eliminar un movimiento de existencia al cual no tiene permiso.'))
                if rec.state == 'draft' and not (self.is_origin_location_attendant(cr, uid, ids, rec, context=context)
                                              or self.is_destiny_location_attendant(cr, uid, ids, rec, context=context)):
                    raise osv.except_osv(_('Warning!'),
                                         _('No puede eliminar un movimiento de existencia al cual no tiene permiso.'))
        return super(grp_almacen_lineas, self).unlink(cr, uid, ids, context=context)

    def _prepare_picking_assign(self, cr, uid, move, context=None):
        values = super(grp_almacen_lineas, self)._prepare_picking_assign(cr, uid, move, context=context)
        values.update({
            'location_id': move.location_id.id,
            'location_dest_id': move.location_dest_id.id,
        })
        return values

class stock_change_product_qty_ext(osv.osv_memory):
    _inherit = "stock.change.product.qty"

    def default_get(self, cr, uid, fields, context):
        """ To get default values for the object.
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param fields: List of fields for which we want default values
         @param context: A standard dictionary
         @return: A dictionary which of fields with values.
        """

        res = super(stock_change_product_qty_ext, self).default_get(cr, uid, fields, context=context)

        if 'location_id' in fields:
            location_id = res.get('location_id', False)
            if not location_id:
                try:
                    model, location_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'stock',
                                                                                             'stock_location_stock')
                except (orm.except_orm, ValueError):
                    pass
            res['location_id'] = location_id
            # quitando el location
            res['location_id'] = False
        return res

class grp_warehouse(osv.osv):
    _inherit = "stock.warehouse"

    _columns = {
        'encargado_ids': fields.many2many('res.users', 'grp_warehouse_user_rel', 'warehouse_id', 'user_id',
                                          string='Encargados', copy=False),
    }

class grp_pedir_abestecimiento(osv.osv_memory):
    _inherit = 'make.procurement'
    _columns = {
        'campo_relacion': fields.many2one('product.product'),
        'precio': fields.related('campo_relacion', 'standard_price', relation='many2one', type='float'),
    }

    def make_procurement(self, cr, uid, ids, context=None):
        """ Creates procurement order for selected product.
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: List of IDs selected
        @param context: A standard dictionary
        @return: A dictionary which loads Procurement form view.
        """
        wh_obj = self.pool.get('stock.warehouse')
        procurement_obj = self.pool.get('grp.solicitud.compra')  # aca tiene que ser Solicitud de compra
        procure_id = False
        for proc in self.pool.get('make.procurement').browse(cr, uid, ids, context=context):
            procure_id = procurement_obj.create(cr, uid, {
                'almacen': proc.warehouse_id.id,
                'product_id': proc.product_id.id,
                'cantidad_solicitada': proc.qty,
                'solicitante_id': uid,
                'company_id': self.pool.get('res.company')._company_default_get(cr, uid, 'product.template',
                                                                                context=context),
                'precio_estimado': proc.product_id.standard_price,
                'uom_id': proc.product_id.uom_id.id,
            })
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'grp.solicitud.compra',
            'res_id': procure_id,
        }

class stock_partial_picking_ext(osv.TransientModel):
    _inherit = "stock.transfer_details"

    @api.constrains('item_ids', 'packop_ids')
    def _check_quantity(self):
        for row in self:
            prod_dict = {}
            for lstits in [row.item_ids, row.packop_ids]:
                for prod in lstits:
                    if prod.product_id in prod_dict:
                        prod_dict[prod.product_id][0] += prod.quantity
                        prod_dict[prod.product_id][1] += prod.packop_id.product_qty or 0.0
                    else:
                        prod_dict[prod.product_id] = [prod.quantity,prod.packop_id.product_qty or 0.0]
            for producto, cantidades in prod_dict.items():
                if cantidades[1] < cantidades[0]:
                    raise exceptions.ValidationError("La cantidad %s del producto %s es mayor que la cantidad permitida, debe ser menor o igual que %s" % (cantidades[0], producto.name, cantidades[1]))


    @api.one
    def do_detailed_transfer(self):
        res = super(stock_partial_picking_ext, self).do_detailed_transfer()
        obj_recursos_line_sr = self.env['grp.compras.solicitud.recursos.line.sr']
        if self.picking_id.doc_origin:
            send_email = False
            for wizard_line in self.picking_id.move_lines:
                # if self.picking_id.picking_type_id.code == 'outgoing':
                if not send_email and wizard_line.line_sr_id and wizard_line.line_sr_id.product_id and wizard_line.product_id \
                   and wizard_line.line_sr_id.product_id.id != wizard_line.product_id.id:
                    send_email = True

                line_sr_product_id = wizard_line.line_sr_id and wizard_line.line_sr_id.product_id \
                                     and wizard_line.line_sr_id.product_id.id \
                                     or wizard_line.product_id.id
                show_sr_uom = wizard_line.with_context(form_view_ref=False).show_sr_uom
                domain = [('grp_id', '=', self.picking_id.doc_origin.sr_id.id), ('product_id', '=', line_sr_product_id)]
                if wizard_line.line_sr_id:
                    domain.append(('id','=',wizard_line.line_sr_id.id))
                for id_line in obj_recursos_line_sr.search(domain):
                    quantity_update = 0
                    if wizard_line.reserved_availability and wizard_line.product_uom_qty > wizard_line.reserved_availability:
                        quantity_update = wizard_line.reserved_availability
                    else:
                        quantity_update = show_sr_uom and wizard_line.sr_product_uom_qty or wizard_line.product_uom_qty
                    #se convierte la cantidad a la UOM de la SR si son distintas
                    product_uom = show_sr_uom and wizard_line.sr_product_uom or wizard_line.product_uom
                    if product_uom.id != id_line.uom_id.id:
                        quantity_update = self.env['product.uom']._compute_qty(product_uom.id, quantity_update, id_line.uom_id.id)

                    if self.picking_id.picking_type_id.code == 'incoming':
                        quantity_update *= (-1)
                    if wizard_line.cantidad_solicitada == id_line.cantidad_solicitada:
                        if id_line.cantidad_entregada + quantity_update < id_line.cantidad_solicitada:
                            if self.picking_id.doc_origin.state in ['aprobado']:
                                wf_service = netsvc.LocalService("workflow")
                                wf_service.trg_validate(self._uid, 'grp.compras.solicitud.recursos.almacen',
                                                        self.picking_id.doc_origin.id,
                                                        'button_wkf_sr_aprobado_esperando_almacen', self._cr)
                            id_line.write({
                                'cantidad_entregada': id_line.cantidad_entregada + quantity_update,
                                'boton_check': False,
                                'estado': 'parcial',
                            })
                        elif id_line.cantidad_entregada + quantity_update == id_line.cantidad_solicitada:
                            id_line.write({
                                'cantidad_entregada': id_line.cantidad_entregada + quantity_update,
                                'boton_check': False,
                                'estado': 'total',
                            })
                        else:
                            raise exceptions.ValidationError(u"El producto %s ya ha sido"
                                                             u" transferido en su totalidad para la SR: %s"
                                                             % (wizard_line.product_id.name,
                                                                self.picking_id.doc_origin.sr_id.name))
                    # if id_line.cantidad_entregada != quantity_update and (
                    #         id_line.cantidad_solicitada - id_line.cantidad_entregada != 0) and wizard_line.cantidad_solicitada == id_line.cantidad_solicitada:
                    #     id_line.write({
                    #         'cantidad_entregada': id_line.cantidad_entregada + quantity_update,
                    #         'boton_check': False,
                    #         'estado': 'parcial',
                    #     })

            if send_email:
                # Notificar al usuario que creó la Solicitud de Recursos
                sr = self.picking_id.doc_origin
                base_url = self.env['ir.config_parameter'].get_param('web.base.url')
                partner_ids = [ sr.solicitante_id.partner_id.id ]
                body = u""" Se entregará un producto similar al producto original solicitado en la Solicitud de Recursos <a href="%(base_url)s/web#id=%(sr_id)s&view_type=form&model=grp.compras.solicitud.recursos.almacen">%(sr_name)s</a>""" \
                    % { 'base_url': base_url,
                        'sr_name': sr.name,
                        'sr_id': sr.id,
                      }

                vals = {
                    'subject': 'Cambio de producto en Solicitud de Recursos',
                    'body_html': '<pre>%s</pre>' % body,
                    'recipient_ids': [(6, 0, partner_ids)],
                    'email_from': self.write_uid.email
                }
                mail_rec = self.env['mail.mail'].create(vals)
                mail_rec.send()

            wf_service = netsvc.LocalService("workflow")
            wf_service.trg_validate(self._uid, 'grp.compras.solicitud.recursos.almacen', self.picking_id.doc_origin.id,
                                    'verificar_stock', self._cr)
        return res

    # Incidencia 68
    def default_get(self, cr, uid, fields, context=None):
        if context is None: context = {}
        res = super(stock_partial_picking_ext, self).default_get(cr, uid, fields, context=context)
        picking_ids = context.get('active_ids', [])
        active_model = context.get('active_model')

        if not picking_ids or len(picking_ids) != 1:
            # Partial Picking Processing may only be done for one picking at a time
            return res
        assert active_model in ('stock.picking'), 'Bad context propagation'
        picking_id, = picking_ids
        picking = self.pool.get('stock.picking').browse(cr, uid, picking_id, context=context)
        items = []
        packs = []
        if not picking.pack_operation_ids:
            picking.do_prepare_partial()
        index = 0
        for op in picking.pack_operation_ids:
            item = {
                'packop_id': op.id,
                'product_id': op.product_id.id,
                'product_uom_id': op.product_uom_id.id,
                # 'quantity': op.picking_id.move_lines[index].product_uom_qty, cambiado a original 13/10
                'quantity': op.product_qty,
                'package_id': op.package_id.id,
                'lot_id': op.lot_id.id,
                'sourceloc_id': op.location_id.id,
                'destinationloc_id': op.location_dest_id.id,
                'result_package_id': op.result_package_id.id,
                'date': op.date,
                'owner_id': op.owner_id.id,
            }
            if op.product_id:
                items.append(item)
            elif op.package_id:
                packs.append(item)
            index = index + 1
        res.update(item_ids=items)
        res.update(packop_ids=packs)
        return res

class product_template(osv.osv):
    _inherit = 'product.template'

    _columns = {
        'prod_tmpl_ret_ids': fields.many2many('account.retention', 'ret_prod_tmpl_rel', 'prod_tmpl_id', 'ret_id',
                                              string='Retenciones producto', ondelete='restrict', copy=False)
    }

# TODO GAP 247 Spring 4: Redefiniendo el metodo que crea los asientos para q lo haga con la nueva fecha
class stock_quant(osv.osv):
    _inherit = "stock.quant"

    def _prepare_account_move_line(self, cr, uid, move, qty, cost, credit_account_id, debit_account_id, context=None):
        res = super(stock_quant, self)._prepare_account_move_line(cr, uid, move, qty, cost, credit_account_id, debit_account_id, context=context)
        if move.acc_entry_currency_id:
            res[0][2].update({ 'currency_id': move.acc_entry_currency_id.id,
                               'amount_currency': (move.acc_entry_amount_currency or 0)*qty })
            res[1][2].update({ 'currency_id': move.acc_entry_currency_id.id,
                               'amount_currency': (move.acc_entry_amount_currency or 0)*qty*(-1) })
        return res

    def _create_account_move_line(self, cr, uid, quants, move, credit_account_id, debit_account_id, journal_id,
                                  context=None):
        # group quants by cost
        quant_cost_qty = {}
        for quant in quants:
            if quant_cost_qty.get(quant.cost):
                quant_cost_qty[quant.cost] += quant.qty
            else:
                quant_cost_qty[quant.cost] = quant.qty
        move_obj = self.pool.get('account.move')
        for cost, qty in quant_cost_qty.items():
            move_lines = self._prepare_account_move_line(cr, uid, move, qty, cost,
                                                         credit_account_id, debit_account_id,
                                                         context=context)
            # period_id = context.get('force_period', self.pool.get('account.period').find(cr, uid, move.date, context=context)[0])
            period_id = context.get('force_period',
                                    self.pool.get('account.period').find(cr, uid, move.account_move_date,
                                                                         context=context)[0])
            account_move_id = move_obj.create(cr, uid, {'journal_id': journal_id,
                                                        'line_id': move_lines,
                                                        'period_id': period_id,
                                                        # 'date': move.date,
                                                        'date': move.account_move_date,
                                                        'ref': move.picking_id.name}, context=context)
            self.pool.get('stock.move').write(cr, uid, move.id, {'account_move_id': account_move_id}, context)

class stock_inventory(osv.osv):
    _inherit = "stock.inventory"

    def action_done(self, cr, uid, ids, context=None):
        """ Finish the inventory
        @return: True
        """
        for inv in self.browse(cr, uid, ids, context=context):
            for inventory_line in inv.line_ids:
                #if inventory_line.product_qty < 0 and inventory_line.product_qty != inventory_line.theoretical_qty:
                if inventory_line.product_qty < 0: #Esto es un pedido del cliente, el original de Odoo (arriba) si lo permite
                    raise osv.except_osv('Advertencia', u'No puede establecer una cantidad negativa de producto en una línea de inventario:\n%s - Cantidad: %s' % (inventory_line.product_id.name, inventory_line.product_qty))
            self.action_check(cr, uid, [inv.id], context=context)
            self.write(cr, uid, [inv.id], {'state': 'done'}, context=context)
            self.post_inventory(cr, uid, inv, context=context)
        return True

    # TODO GAP 247 Spring 4: Agregando el campo fecha de asiento
    _columns = {
        'account_move_date': fields.date('Fecha asiento', states={'done': [('readonly', True)]}, select=True),
    }

    # TODO GAP 247 Spring 4: Redefiniendo el metodo para que el asiento se cree con la fecha de asiento
    def post_inventory(self, cr, uid, inv, context=None):
        move_obj = self.pool.get('stock.move')
        if inv.account_move_date:
            move_obj.write(cr, uid, [x.id for x in inv.move_ids], {'account_move_date': inv.account_move_date}, context=context)
        return super(stock_inventory, self).post_inventory(cr, uid, inv, context=context)
