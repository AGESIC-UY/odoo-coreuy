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

from openerp.osv import fields, osv
from openerp import SUPERUSER_ID
import time


class grp_solicitar_compra(osv.osv_memory):
    _name = 'grp.solicitar.compra'
    _description = 'Make Procurements'
    _columns = {
        'solicitud_id': fields.many2one('grp.compras.solicitud.recursos.almacen', required=True),
        'grp_sr_id': fields.related('solicitud_id', 'grp_sr_id', type='one2many',
                                    relation='grp.compras.solicitud.recursos.line.sr'),
        'warehouse': fields.related('solicitud_id', 'warehouse', type='many2one', relation='stock.warehouse',
                                    string=u'Almacén', readonly=True),
    }

    def read(self, cr, uid, ids, fields=None, context=None, load='_classic_read'):
        result = super(grp_solicitar_compra, self).read(cr, uid, ids, fields=fields, context=context, load=load)
        if fields and 'grp_sr_id' in fields:
            for r in result:
                line_ids = []
                for line_id in r.get('grp_sr_id', []):
                    line = self.pool['grp.compras.solicitud.recursos.line.sr'].browse(cr, uid, line_id)
                    if line.product_id and \
                       (line.product_id.type=='service' or \
                        (line.product_id.type=='consu' and line.product_id.no_inventory)):
                        continue
                    line_ids.append(line_id)
                r['grp_sr_id'] = line_ids
        return result

    def button_solicitar_productos(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        context = dict(context)
        wiz = self.browse(cr, uid, ids, context=context)[0]
        lines_pool= self.pool.get('grp.compras.solicitud.recursos.line.sr')
        sr_pool = self.pool.get('grp.compras.solicitud.recursos.almacen')
        sc_ids = []
        for line in wiz.grp_sr_id:
            if not line.cantidad_pedida or \
               (line.product_id and (line.product_id.type=='service' or (line.product_id.type=='consu' and line.product_id.no_inventory))):
                continue
            elif line.cantidad_pedida < 0:
                raise osv.except_osv('Error!', u'No se puede ingresar una cantidad pedida negativa.')
            elif not line.product_id:
                raise osv.except_osv('Error!', u'Una línea no tiene producto seleccionado! Seleccione el producto antes de realizar el pedido')
            elif line.cantidad_pedida + line.cantidad_entregada + line.cantidad_en_pedido > line.cantidad_solicitada:
                raise osv.except_osv('Error!', u'No se puede pedir mayor cantidad a la solicitada (' + unicode(line.product_id.name) + u')')
            else:
                context.update({'es_wizard': True})
                sc_id = self.pool.get('grp.solicitud.compra')._crear_solicitud_linea(cr, uid, line, context=context)
                sc_ids.append(sc_id)
                # PCARBALLO -- Se cambia el valor de boton_check a False y el estado a Enviado a compras.
                lines_pool.write(cr, SUPERUSER_ID, [line.id], {'cantidad_en_pedido': line.cantidad_pedida + line.cantidad_en_pedido, 'boton_check': False, 'estado': 'acompra'})
                cr.execute("""  select partner_id from res_users where id = %s""", (uid,))
                cli = cr.fetchone()[0]
                subject = u'SR Cambio de Sub-estado'
                message = self.pool.get('mail.message')
                message.create(cr, uid, {
                    'res_id': ids[0],
                    'date': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'author_id': cli,
                    'model': self._name,
                    'subject': subject,
                    'body': u'Solicitud de Recursos ha cambiado al sub-estado: Enviado a Compras',
                }, context=context)
                sr_almacen_id = sr_pool.search(cr, uid, [('sr_id', '=', line.grp_id.id)], context=context)
                sr_pool.write(cr, SUPERUSER_ID, sr_almacen_id, {'estado_en_proc': 'envcomp'})

        dummy, action_id = self.pool.get('ir.model.data').get_object_reference(
                            cr, uid, 'grp_compras_estatales', 'action_grp_solicitud_compra')
        action = self.pool.get('ir.actions.act_window').read(cr, uid, [action_id], context=context)[0]
        action.update({
            'name': u"Solicitudes de compras",
            'domain': "[('id', 'in', %s)]" % (sc_ids),
            'context': context,
        })
        return action

grp_solicitar_compra()

