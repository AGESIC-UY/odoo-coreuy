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

from openerp.osv import osv, fields
import datetime
import openerp.addons.decimal_precision as dp
import time
from openerp.tools.translate import _
from openerp import SUPERUSER_ID, netsvc, api
from openerp.exceptions import ValidationError
from openerp.tools.sql import drop_view_if_exists
from openerp.addons.base_suspend_security.base_suspend_security import BaseSuspendSecurityUid

import logging

_logger = logging.getLogger(__name__)

_ESTADO_HISTORIAL_RESP = [('AC', 'Aceptado'), ('EP', 'En proceso'), ('RE', 'Rechazado')]

class grp_compras_solicitud_recursos(osv.osv):
    _inherit = ['mail.thread']
    _description = 'Solicitud de Recursos'
    _name = 'grp.compras.solicitud.recursos'

    _mail_post_access = 'read'

    def _get_solicitante_editable(self, cr, uid, ids, name, args, context=None):
        res = {}
        in_grp = self.pool.get('res.users').has_group(cr, uid, 'grp_seguridad.grp_compras_sr_Solicitante')
        for record in self.browse(cr, uid, ids, context=context):
            res[record.id] = (record.state in ('inicio', 'nuevo')) and in_grp
        return res

    def _get_aprobador_editable(self, cr, uid, ids, name, args, context=None):
        res = {}
        in_grp = self.pool.get('res.users').has_group(cr, uid, 'grp_seguridad.grp_compras_sr_Aprobador')
        for record in self.browse(cr, uid, ids, context=context):
            res[record.id] = (record.state in ('en_aprobacion')) and in_grp
        return res

    def _get_almacenero_editable(self, cr, uid, ids, name, args, context=None):
        res = {}
        in_grp = self.pool.get('res.users').has_group(cr, uid,
                                                      'grp_seguridad.grp_compras_sr_Encargado_de_almacen')
        for record in self.browse(cr, uid, ids, context=context):
            res[record.id] = (record.state in ('codificando', 'esperando_almacen')) and in_grp
        return res

    LISTA_ESTADOS_SOLICITUD = [
        ('inicio', 'Borrador'),
        ('en_aprobacion', u'En aprobación'),
        ('rechazado', 'Rechazado'),
        ('codificando', u'Aprobado'),
        ('esperando_almacen', u'En Proceso'),
        ('aprobado', 'Cerrado'),
    ]

    ##################################################
    ### FUNCIÓN QUE CREA LAS SC A PARTIR DE LAS SR ###
    ##################################################
    def merge_sr(self, cr, uid, ids, context=None):
        '''
             @return: purchase order view
        '''
        solicitud_obj = self.pool.get('grp.solicitud.compra')
        solicitud_obj.do_merge_sr(cr, uid, context.get('active_ids', []), context)
        return True

    def onchange_solicitante_id(self, cr, uid, ids, solicitante_id):
        value = {}
        if solicitante_id:
            value = {'department_id': self.pool.get('res.users').get_departamento(cr, uid, solicitante_id)}
        return {'value': value}

    # PCARBALLO -- Funciones get y set para el campo funcional presup_view_line_copy, de tipo one2many
    def _get_lineas_presup_line(self, cr, uid, ids, fields, args, context=None):
        line_obj = self.pool.get('grp.compras.solicitud.recursos.line.sr')
        res = {}
        for obj in self.browse(cr, uid, ids):
            args = [('estado', 'in', ['enaprobcom']), ('grp_id', '=', obj.id)]
            if obj.ir_filter_id:
                args += eval(obj.ir_filter_id.domain)
            line_ids = line_obj.search(cr, uid, args)
            res[obj.id] = line_ids
        return res

    def _set_lineas_presup_line(self, cr, uid, id, name, value, inv_arg, context):
        line_obj = self.pool.get('grp.compras.solicitud.recursos.line.sr')
        for line in value:
            if line[0] == 1:  # one2many Update
                line_id = line[1]
                line_obj.write(cr, uid, [line_id], line[2])
        return True

    def crear_solicitud_compra(self, cr, uid, ids, context=None):
        sc_pool = self.pool.get('grp.solicitud.compra')
        for lines in self.browse(cr, uid, ids, context=context)[0].grp_sr_id:
            if not sc_pool.search(cr, uid, [('linea_solicitud_recursos_id','=',lines.id)], context=context):
                sc_pool._crear_solicitud_linea(cr, uid, lines, context=context)
        return True

    # def _get_tipo_sr(self, cr, uid, context=None):
    #     res = [
    #         ('I', 'Insumos/Materiales'),
    #         ('S', 'Servicios'),
    #         ('AF', 'Activo Fijo'),
    #         ('PL', 'Planificada'),
    #     ]
    #     return res

    def _get_lista_tipo_sr(self, cr, uid, context=None):
        es_solic_planif = self.pool.get('res.users').has_group(cr, uid,
                                                               'grp_compras_estatales.grp_sr_solicitante_planif')
        es_solic_comun = self.pool.get('res.users').has_group(cr, uid, 'grp_seguridad.grp_compras_sr_Solicitante')
        select = [
            ('I', 'Insumos/Materiales'),
            ('S', 'Servicios'),
            ('AF', 'Activo Fijo'),
            ('PL', 'Planificada')
        ]
        if es_solic_comun and not es_solic_planif:
            select = [
                ('I', 'Insumos/Materiales'),
                ('S', 'Servicios'),
                ('AF', 'Activo Fijo')
            ]
        elif es_solic_planif and not es_solic_comun:
            select = [
                ('PL', 'Planificada')
            ]
        return select

    _columns = {
        'name': fields.char('Nro. Solicitud', size=32),  # Nro Solicitud
        'grp_sr_id': fields.one2many('grp.compras.solicitud.recursos.line.sr', 'grp_id', 'Solicitud'),
        'solicitante_id': fields.many2one('res.users', 'Solicitante', readonly=True, copy=False),

        'ir_filter_id': fields.many2one('ir.filters', 'Additional Filter',
                                        domain=[('model_id', '=', 'grp.compras.solicitud.recursos.line.sr')]),

        'presup_view_line_copy': fields.function(_get_lineas_presup_line, fnct_inv=_set_lineas_presup_line,
                                                 relation="grp.compras.solicitud.recursos.line.sr", type="one2many",
                                                 string="Presupuesto"),
        'warehouse': fields.many2one('stock.warehouse', u'Almacén'),

        'encargado_ids': fields.related('warehouse', 'encargado_ids', type="many2many", relation="res.users",
                                       string=u'Encargados de almacén', readonly=True),
        'aprobador_id': fields.many2one('res.users', 'Aprobador', readonly=True, copy=False),
        'company_id': fields.many2one('res.company', u'Compañía', readonly=True),
        'department_id': fields.many2one('hr.department', string=u'Departamento', readonly=True, copy=False),
        'state': fields.selection(LISTA_ESTADOS_SOLICITUD, 'Estado', size=20, track_visibility='onchange'),
        'inciso': fields.char('Inciso'),
        'u_e': fields.char('UE'),
        'tipo_sr': fields.selection(_get_lista_tipo_sr, string='Tipo SR', required=True),  # Estado
        'date_start': fields.date('Fecha de Solicitud', copy=False),  # Fecha de solicitud
        'description': fields.text(u'Observaciones', size=250),  # Descripcion
        'solicitante_editable': fields.function(_get_solicitante_editable, type='boolean', store=False),
        'aprobador_editable': fields.function(_get_aprobador_editable, type='boolean', store=False),
        'almacenero_editable': fields.function(_get_almacenero_editable, type='boolean', store=False),
    }

    ######################## Estados ####################################

    _defaults = {
        'state': 'inicio',
        'name': 'SR-Borrador',
        'company_id': lambda s, cr, uid, c: s.pool.get('res.company')._company_default_get(cr, uid, 'product.template',
                                                                                           context=c),
        'solicitante_id': lambda s, cr, uid, c: uid,
        'department_id': lambda s, cr, uid, c: s.pool.get('res.users').get_departamento(cr, uid, uid),
        'date_start': fields.date.context_today,
        'solicitante_editable': True,
        'aprobador_editable': True,
        'almacenero_editable': False
    }

    @api.constrains('tipo_sr','grp_sr_id')
    def _check_grp_sr_id(self):
        reception_obj = self.env['grp.fecha.planificada']
        for record in self:
            pos_line = 0
            for line in record.grp_sr_id:
                pos_line += 1
                if line.product_id:
                    #Servicios
                    if record.tipo_sr == 'S' and line.product_id.type != 'service':
                        raise ValidationError(u"En la línea %s de la SR, el tipo del producto %s no corresponde con el tipo de la SR. Debe corregir esto para continuar." % (str(pos_line), line.product_id.name))
                    #Activo Fijo
                    if record.tipo_sr == 'AF' and not line.product_id.categ_id.activo_fijo:
                        raise ValidationError(u"En la línea %s de la SR, el tipo del producto %s no corresponde con el tipo de la SR. Debe corregir esto para continuar." % (str(pos_line), line.product_id.name))
                    #Insumos/Materiales
                    if record.tipo_sr == 'I' and (line.product_id.type not in ['consu', 'product'] or line.product_id.categ_id.activo_fijo):
                        raise ValidationError(u"En la línea %s de la SR, el tipo del producto %s no corresponde con el tipo de la SR. Debe corregir esto para continuar." % (str(pos_line), line.product_id.name))
                #Planificada
                if record.tipo_sr == 'PL':
                    date_start = datetime.datetime.strptime(record.date_start, '%Y-%m-%d')
                    reception_rows = reception_obj.search([('year', '=', str(date_start.year))])
                    if reception_rows:
                        for reception in reception_obj.search([('year', '=', str(date_start.year))]):
                            if record.date_start > reception.reception_date:
                                raise ValidationError(u"No se puede crear una SR planificada con una fecha de solicitud posterior a la fecha de recepción correspondiente.")
                    else:
                        raise ValidationError(u"No se puede crear una SR planificada sin tener configurada una fecha de solicitud planificada válida.")

class grp_compras_solicitud_recursos_almacen(osv.osv):
    _name = 'grp.compras.solicitud.recursos.almacen'
    _description = 'Solicitud de Recursos en almacen'
    _inherits = {'grp.compras.solicitud.recursos': 'sr_id'}
    _inherit = ['mail.thread']
    _order = "id desc"

    _mail_post_access = 'read'

    def _domain_almacenero(self, cr, uid, ids, d1, d2, context=None):
        in_grp = self.pool.get('res.users').has_group(cr, uid,
                                                      'grp_seguridad.grp_compras_sr_Encargado_de_almacen')
        res = {}
        for lines in self.browse(cr, uid, ids, context=None):
            res[lines.id] = in_grp and lines.state in ['codificando', 'esperando_almacen']
        return res

    def _cumple_stock(self, cursor, user, ids, name, arg, context=None):
        res = {}
        for sr_almacen in self.browse(cursor, user, ids, context=context):
            res[sr_almacen.id] = all(line.cantidad_pendiente == 0 for line in sr_almacen.grp_sr_id)
        return res

    def onchange_tipo_sr(self, cr, uid, ids, tipo_sr, context=None):
        """Cuando cambia la ubicacion, actualizo el valor del almacen"""
        return {
            'value': {'ubicacion': False},
            'domain': {'ubicacion': [
                ('active','=',True),
                ('usage','=','internal')
            ]}}

    @api.onchange('ubicacion')
    def _onchange_ubicacion(self):
        self.warehouse = False
        # self.warehouse_view = False
        self.encargado_ids = False
        if self.ubicacion:
            _w = self.ubicacion.get_warehouse(self.ubicacion)
            if _w:
                self.warehouse = _w
                # self.warehouse_view = _w
                self.encargado_ids = self.env['stock.warehouse'].browse(_w).encargado_ids

    @api.depends('warehouse')
    def _compute_warehouse_view(self):
        for row in self:
            row.warehouse_view = row.warehouse

    def _get_copy(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for rec in self.browse(cr, uid, ids, context=context):
            res[rec.id] = rec.warehouse.id
        return res

    def button_solicitar_aprobacion(self, cr, uid, ids, context=None):
        sr_ids = self.browse(cr, uid, ids[0], context=context)[0].grp_sr_id
        for sr_line in sr_ids:
            if (sr_line.cantidad_pendiente > 0):
                self.pool.get('grp.compras.solicitud.recursos.line.sr').write(cr, uid, sr_line.id,
                                                                              {'boton_check': True})

        cr.execute("""  select partner_id from res_users where id = %s""",
                   (uid,))
        cli = cr.fetchone()[0]
        subject = u'SR Cambio de Sub-estado'
        message = self.pool.get('mail.message')
        message.create(cr, uid, {
            'res_id': ids[0],
            'date': time.strftime('%Y-%m-%d %H:%M:%S'),
            'author_id': cli,
            'model': self._name,
            'subject': subject,
            'body': u'Solicitud de Recursos ha cambiado al sub-estado: En Aprobación Compras',
        }, context=context)
        self.write(cr, uid, ids, {'check_button_solicitar': True, 'estado_en_proc': 'eaprobcomp'})
        return True

    def _get_en_aprobacion(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for rec in self.browse(cr, uid, ids, context=context):
            acum = False
            for item in rec.grp_sr_id:
                acum = acum or item.boton_check
            res[rec.id] =  acum
        return res

    _columns = {
        'sr_id': fields.many2one('grp.compras.solicitud.recursos', required=True, ondelete='cascade'),
        'warehouse_view': fields.many2one('stock.warehouse', string=u"Almacén", compute='_compute_warehouse_view', readonly=True),
        'ubicacion': fields.many2one('stock.location', u'Ubicación', domain="[('active','=',True),('usage','=','internal')]"),
        'check_aprobacion': fields.function(_get_en_aprobacion, type='boolean',
                                            string=u"Tiene lineas en aprobacion de compra?"),
        'check_button_solicitar': fields.boolean('Ya se presiono el boton de solicitar?'),
        'director': fields.boolean('Director'),
        # condicion para ocultar/mostrar botones
        'domain_almacenero': fields.function(_domain_almacenero, type='boolean', store=False),
        'cumple_stock': fields.function(_cumple_stock, string='Cumple stock', type='boolean'),
        'grp_sr_af_id': fields.one2many('grp.compras.solicitud.recursos.line.sr.af', 'grp_id', 'Solicitud'),
        'description': fields.char(u'Observaciones', size=500),
        'estado_en_proc': fields.selection([
                                                ('eprocalm', u'En proceso almacén'),
                                                ('eaprobcomp', u'En Aprobación Compras'),
                                                ('envcomp', u'Enviado a Depto de compras'),
                                                ('pendrecep', u'Pendiente Recepción'),
                                            ], "Estado en proceso"),
    }

    _defaults = {
        'check_aprobacion': False,
        'check_button_solicitar': False,
        'state': 'inicio',
        'solicitante_id': lambda self, cr, uid, context: uid
    }

    def button_cumplir_af(self, cr, uid, ids, context):
        return {
            'name': _('Activos Fijos'),
            'res_model': 'account.asset.asset',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'tree,form',
            'view_type': 'form',
            'limit': 80,
        }

    def onchange_solicitante_id(self, cr, uid, ids, solicitante_id):
        return self.pool.get('grp.compras.solicitud.recursos').onchange_solicitante_id(cr, uid, ids, solicitante_id)

    # Generacion de solicitudes de compra al estar aprobada la SR (almacen)
    def sr_almacen_aprobada(self, cr, uid, ids, context=None):
        grp_compras_sr_obj = self.pool.get('grp.compras.solicitud.recursos')
        for sr_almacen in self.browse(cr, uid, ids, context=context):
            if not grp_compras_sr_obj.crear_solicitud_compra(cr, uid, [sr_almacen.sr_id.id], context=context):
                return False
        return True

    def unlink(self, cr, uid, ids, context=None):
        sr_almacen_ids = self.browse(cr, uid, ids, context=context)
        sr_a_borrar = len(sr_almacen_ids)
        for sr_almacen in sr_almacen_ids:
            if sr_almacen.state in ('inicio', 'nuevo'):
                super(grp_compras_solicitud_recursos_almacen, self).unlink(cr, uid, ids, context=context)
                sr_a_borrar -= 1
        if sr_a_borrar > 0:
            raise osv.except_osv('Error!', u'Solamente de puede eliminar las SR en estado borrador')
        else:
            return True

    # al pasar el estado a 'en_aprobacion' se asigna nuevo número de SR
    # Se envian mensajes
    def act_sr_almacen_aprobacion(self, cr, uid, ids, context=None):
        _logger.info('act_sr_almacen_aprobacion')
        vals = {}
        context = dict(context or {})
        for r in self.browse(cr, uid, ids, context=context):
            if not r.grp_sr_id:
                raise osv.except_osv(_('Error!'), _('No puede enviar a aprobar una solicitud que no tiene líneas.'))
            vals['state'] = 'en_aprobacion'
            fiscalyear_obj = self.pool.get('account.fiscalyear')
            uid_company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
            fecha_hoy = r.date_start
            if fecha_hoy:
                fiscal_year_id = fiscalyear_obj.search(cr, uid,
                                                       [('date_start', '<=', fecha_hoy), ('date_stop', '>=', fecha_hoy),
                                                        ('company_id', '=', uid_company_id)], context=context)
                fiscal_year_id = fiscal_year_id and fiscal_year_id[0] or False
                context.update({'fiscalyear_id': fiscal_year_id})
            sequence = self.pool.get('ir.sequence').get(cr, uid, 'resource.requisition.number', context=context)
            ind= sequence.index('-') +1
            inciso = self.pool.get('res.company').browse(cr, uid, uid_company_id, context=context).inciso
            vals['name'] =  sequence[0:ind] +inciso + sequence[ind:len(sequence)]
            self.write(cr, uid, [r.id], vals, context=context)
            self.send_notification(cr, uid, r, u'En aprobación', context=context)
        return True

    def send_notification(self, cr, uid, rs, state, context=None):
        rs_row = self.browse(cr, uid, rs.id, context=context)
        group_id = self.pool.get('res.groups').get_group_by_ref(cr, uid,
            rs_row.tipo_sr == 'PL' and 'grp_compras_estatales.grp_sr_solicitante_planif' or 'grp_seguridad.grp_compras_sr_Aprobador')
        if group_id:
            partner_ids = [
                user_ingroup.partner_id.id for user_ingroup in self.pool.get('res.groups').browse(cr, uid, group_id[0], context=context).users \
                if rs_row.department_id and rs_row.department_id.id in [e.department_id.id for e in user_ingroup.employee_ids]
            ]
            if partner_ids:
                msg = _(u"Solicitud de recursos en almacén Nro %s cambiado a estado %s por usuario %s") % \
                        (rs_row.name, state, self.pool.get('res.users').browse(cr, uid, uid, context=context).name)
                self.message_post(cr, uid, [rs_row.id], body=msg, type='notification', subtype='mt_comment',
                                partner_ids=partner_ids, context=context)

    # Se debe poner en el campo 'aprobador' el nombre de quien aprueba
    def act_sr_almacen_codificando(self, cr, uid, ids, context=None):
        lines_pool = self.pool.get('grp.compras.solicitud.recursos.line.sr')
        sc_pool = self.pool.get('grp.solicitud.compra')
        for r in self.browse(cr, uid, ids, context=context):
            self.write(cr, uid, [r.id],
                       {'date_approved': time.strftime('%Y-%m-%d'), 'state': 'codificando', 'aprobador_id': uid},
                       context=context)

            ## Crear de forma automática una solicitud de compras para las líneas
            ## con productos consumibles no inventariables o productos servicios
            for line in r.grp_sr_id:
                if line.product_id and \
                  (line.product_id.type=='service' or (line.product_id.type=='consu' and line.product_id.no_inventory)):
                    if line.cantidad_pedida < 0:
                        raise osv.except_osv('Error!', u'No se puede ingresar una cantidad pedida negativa.')
                    elif line.cantidad_pedida + line.cantidad_entregada + line.cantidad_en_pedido > line.cantidad_solicitada:
                        raise osv.except_osv('Error!', u'No se puede pedir mayor cantidad a la solicitada (' + unicode(line.product_id.name) + u')')

                    lines_pool.write(cr, SUPERUSER_ID, [line.id],
                                     {'cantidad_pedida': max(0, line.cantidad_solicitada - line.cantidad_entregada - line.cantidad_en_pedido)},
                                     {'solicitar_compra': True})

                    ctx = dict(context or {}, es_wizard=True)
                    sc_pool._crear_solicitud_linea(cr, uid, line, context=ctx)
                    lines_pool.write(cr, SUPERUSER_ID, [line.id], {'cantidad_en_pedido': line.cantidad_pedida + line.cantidad_en_pedido, 'boton_check': False, 'estado': 'acompra'})

        return True

    def act_sr_almacen_esperando_almacen(self, cr, uid, ids, context=None):
        sc_pool = self.pool.get('grp.solicitud.compra')
        for r in self.browse(cr, uid, ids, context=context):
            __uid = uid
            if (hasattr(r, 'solicitar_compra') and r.solicitar_compra) or r.all_products_no_stockable():
                __uid = BaseSuspendSecurityUid(uid)
            if r.tipo_sr in ['AF']:
                lista = []
                for line in r.grp_sr_id:
                    if line.product_id.id:
                        #se crea tantas lineas como la cantidad solicitada
                        for x in range(int(line.cantidad_solicitada)):
                            lista.append((0, 0, {'product_id': line.product_id.id}))

                if lista:
                    fields = {
                        'grp_sr_af_id': lista,
                    }
                    self.write(cr, __uid, [r.id], fields,
                               context=context)

            if r.tipo_sr not in ['S']:
                cr.execute("""  select partner_id from res_users where id = %s""",
                           (uid,))
                cli = cr.fetchone()[0]
                subject = u'SR Cambio de Sub-estado'
                message = self.pool.get('mail.message')
                message.create(cr, __uid, {
                    'res_id': ids[0],
                    'date': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'author_id': cli,
                    'model': self._name,
                    'subject': subject,
                    'body': u'Solicitud de Recursos ha cambiado al sub-estado: En Proceso Almacenero',
                }, context=context)
                self.write(cr, __uid, [r.id], {'state': 'esperando_almacen', 'estado_en_proc': 'eprocalm'},
                           context=context)
            else:
                cr.execute("""  select partner_id from res_users where id = %s""",
                           (uid,))
                cli = cr.fetchone()[0]
                subject = u'SR Cambio de Sub-estado'
                message = self.pool.get('mail.message')
                message.create(cr, __uid, {
                    'res_id': ids[0],
                    'date': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'author_id': cli,
                    'model': self._name,
                    'subject': subject,
                    'body': u'Solicitud de Recursos ha cambiado al sub-estado: Enviado a Compras',
                }, context=context)
                self.write(cr, __uid, [r.id], {'state': 'esperando_almacen', 'estado_en_proc': 'envcomp'},
                           context=context)

            # Si la SR tiene una solicitudes de compras asociadas, se deben actualizar
            # los campos “producto” (product_id)  y “cantidad solicitada” (cantidad_solicitada)
            # de la SC con los datos de la SR de estos productos.
            for line in r.grp_sr_id:
                sc_ids = sc_pool.search(cr, __uid, [('linea_solicitud_recursos_id','=',line.id)], context=context)
                if sc_ids:
                    vals_updated = sc_pool._prepare_crear_solicitud_linea(cr, __uid, line)
                    vals_updated.pop('linea_solicitud_recursos_id', None)
                    vals_updated.pop('company_id', None)
                    sc_pool.write(cr, __uid, sc_ids, vals_updated, context=context)

        return True


    # Se debe poner en el campo 'aprobador' el nombre de quien rechaza
    def act_sr_almacen_rechazado(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'rechazado', 'aprobador_id': uid}, context=context)
        return True

    def act_sr_almacen_aprobado(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'aprobado'}, context=context)
        return True

    def get_tipo_sc(self, cr, uid, ids, context=None):
        s_r = self.browse(cr, uid, ids, context=context)[0]
        return s_r.tipo_sr == 'PL'

    def all_products_no_stockable(self, cr, uid, ids, context=None):
        for sr in self.browse(cr, uid, ids, context=context):
            if not sr.grp_sr_id:
                return False
            for line in sr.grp_sr_id:
                if not line.product_id:
                    return False
                if line.product_id.type in ('product','consu') and \
                   not line.product_id.no_inventory:
                    return False
        return True

    def has_stockable_products(self, cr, uid, ids, context=None):
        for sr in self.browse(cr, uid, ids, context=context):
            for line in sr.grp_sr_id:
                if line.product_id and line.product_id.type in ('product','consu') and \
                   not line.product_id.no_inventory:
                    return True
        return False

    def act_sr_generar_sc(self, cr, uid, ids, context=None):
        for r in self.browse(cr, uid, ids, context=context):
            if not self.sr_almacen_aprobada(cr, uid, ids, context=context):
                raise osv.except_osv('Error!', u'Generando SC desde SR almacen')
            if r.tipo_sr == 'S':
                self.change_en_aprobacion_a_almacen_en_proceso(cr, uid, r.id, context=context)
        return True

    def sr_aprobar_planificada(self, cr, uid, ids, context=None):
        for r in self.browse(cr, uid, ids, context=context):
            self.act_sr_generar_sc(cr, uid, [r.id], context=context)
            wf_service = netsvc.LocalService("workflow")
            wf_service.trg_validate(uid, 'grp.compras.solicitud.recursos.almacen', r.id,
                                    'aprobar_planificada', cr)
        return True

    def change_en_aprobacion_a_almacen_en_proceso(self, cr, uid, id, context=None):
        if not isinstance(id, (list,)):
            id = [id]
        s_r = self.browse(cr, uid, id[0], context=context)
        for line in s_r.grp_sr_id:
            line.write({'estado': 'acompra'})
        self.write(cr, uid, id, {'state': 'esperando_almacen', 'estado_en_proc': 'envcomp'}, context=context)
        return True

    def act_sr_cerrar_almacen(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'aprobado'}, context=context)
        return True

    def trans_sr_almacen_codificando_esperando_almacen(self, cr, uid, ids, context=None):
        if not ids or len(ids) < 1:  # No refiere a registro alguno
            return True
        sr_brw = self.browse(cr, uid, ids, context=context)
        if not sr_brw or len(sr_brw) < 1:  # No encuentra registros con esos ids
            return True
        for line in sr_brw[0].grp_sr_id:  # Se asume que solamente retorna una fila
            if not line.product_id:
                raise osv.except_osv('Error!',
                                     u'Una línea no tiene producto seleccionado! Seleccione el producto antes de realizar el pedido (' + unicode(
                                         line.descripcion) + u')')
        #Para SR de Insumos/materiales se controla que quien valide sea encargado del almacen de la SR
        if sr_brw.tipo_sr == 'I':
            encargados = [e.id for e in sr_brw.encargado_ids]
            if uid not in encargados:
                raise osv.except_osv('Error!', u"No se ha podido validar esta solicitud porque usted no se encuentra configurado "
                                               u"como Encargado/a de Almacén de la ubicación seleccionada. "
                                               u"Por favor revise la ubicación o contacte al Encargado/a de Almacén correspondiente")
        return True

    def button_solicitar_compra(self, cr, uid, ids, context=None):
        s_r = self.browse(cr, uid, ids, context=context)[0]
        lines_pool = self.pool.get('grp.compras.solicitud.recursos.line.sr')
        for lines in s_r.grp_sr_id:
            lines_pool.write(cr, SUPERUSER_ID, [lines.id],
                             {'cantidad_pedida': max(0, lines.cantidad_solicitada - lines.cantidad_entregada - lines.cantidad_en_pedido)},
                             {'solicitar_compra': True})

        wizard_pool = self.pool.get('grp.solicitar.compra')
        solicitud = s_r
        wizard_id = wizard_pool.create(cr, uid, {'solicitud_id': solicitud.id}, context=context)
        model_pool = self.pool.get('ir.model.data')
        id2 = model_pool._get_id(cr, uid, 'grp_compras_estatales', 'view_solicitud_compra_wizard')
        if id2:
            id2 = model_pool.browse(cr, uid, id2, context=context).res_id
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'grp.solicitar.compra',
            'res_id': wizard_id,
            'views': [(id2, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'new'
        }

    def _prepare_move_line(self, cr, uid, ids, cabezal, lineas_solicitud, location_dest_id, pick_type_id, context=None):
        return {
            'product_id': lineas_solicitud.product_id.id,
            'product_uom_qty': lineas_solicitud.cantidad_pendiente,
            'cantidad_solicitada': lineas_solicitud.cantidad_solicitada,
            'product_uom': lineas_solicitud.uom_id.id,
            'location_dest_id': location_dest_id,
            'location_id': cabezal.ubicacion and cabezal.ubicacion.id or False,
            'picking_type_id': pick_type_id,
            'date': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'date_expected': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'name': lineas_solicitud.descripcion,
            'invoice_state': 'none',
            'procure_method': 'make_to_stock',
            'state': 'draft',
            'line_sr_id': lineas_solicitud.id,
        }

    def button_view_pickings(self, cr, uid, ids, context=None):
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'stock.picking',
            'domain': [('doc_origin', 'in', ids)]
        }

    def button_view_pedidos(self, cr, uid, ids, context=None):
        linea_pedido_obj = self.pool.get('grp.linea.pedido.compra')
        solicitud_compra_obj = self.pool.get('grp.solicitud.compra')
        sc_ids = solicitud_compra_obj.search(cr, uid, [('solicitud_recursos_id','in',ids)], context=context)
        line_pc_ids = linea_pedido_obj.search(cr, uid, [('solicitud_compra_id','in',sc_ids)], context=context)
        pedido_ids = []
        for linea in linea_pedido_obj.browse(cr, uid, line_pc_ids, context=context):
            if linea.pedido_compra_id.id not in pedido_ids:
                pedido_ids.append(linea.pedido_compra_id.id)
        if not pedido_ids:
            raise ValidationError(u"No existen pedidos de compra para esta SR")
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'grp.pedido.compra',
            'domain': [('id', 'in', pedido_ids)]
        }

    def button_cumplir_stock(self, cr, uid, ids, context=None):
        stock_picking_type = self.pool.get('stock.picking.type')
        cabezal = self.browse(cr, uid, ids[0], context=context)
        view_ref = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'stock', 'view_picking_form')
        view_id = view_ref and view_ref[1] or False
        if not ids:
            return False
        ctx = {}
        if context:
            ctx = context.copy()
        ctx['default_origin'] = cabezal.sr_id.name
        ctx['default_doc_origin'] = cabezal.id
        ctx['default_warehouse'] = cabezal.warehouse and cabezal.warehouse.id or False,
        ctx['default_solicitante_id'] = cabezal.sr_id.solicitante_id.id,
        lines_list = []

        pick_type_id = stock_picking_type.search(cr, uid,
                                                    [('warehouse_id', '=', ctx['default_warehouse']),
                                                   ('code', '=', 'outgoing')], limit=1, context=context)
        pick_type_id = pick_type_id and pick_type_id[0] or False
        if pick_type_id:
            stock_picking_type_row = stock_picking_type.browse(cr, uid, pick_type_id, context=context)
            location_dest_id = stock_picking_type_row.default_location_dest_id and stock_picking_type_row.default_location_dest_id.id or False
        location_id = cabezal.ubicacion and cabezal.ubicacion.id or False

        for lineas_solicitud in cabezal.grp_sr_id:
            if lineas_solicitud.cantidad_pendiente and \
               not (lineas_solicitud.product_id.type=='service' or (lineas_solicitud.product_id.type=='consu' and lineas_solicitud.product_id.no_inventory)):
                date_today = datetime.date.today()
                date_formatted = date_today.strftime('%Y-%m-%d %H:%M:%S')
                lines_list.append((0, 0, self._prepare_move_line(cr, uid, ids, cabezal, lineas_solicitud, location_dest_id, pick_type_id, context=context)))
        ctx['default_picking_type_id'] = pick_type_id
        ctx['default_location_id'] = location_id
        ctx['default_location_dest_id'] = location_dest_id
        ctx['default_move_type'] = 'direct'
        if lines_list:
            ctx['default_move_lines'] = lines_list
            return {
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'stock.picking',
                'context': ctx,
            }
        else:
            raise osv.except_osv('Error!',
                                 u'Se ha entregado todo el stock correspondiente a la solicitud de recursos seleccionada!')

    def button_add_line_sr(self, cr, uid, ids, context=None):
        values = {}
        values['grp_id'] = ids[0]
        values['cantidad_pedida'] = 0
        values['cantidad_solicitada'] = 0
        values['cantidad_en_pedido'] = 0
        values['domain_solicitante'] = True
        values['domain_almacenero'] = False
        values['domain_aprobador'] = False
        values['descripcion'] = ' '
        # por default va el primer registro cuyo name contenga "unit"
        product_uom_ids = self.pool.get('product.uom').search(cr, uid, [('name', 'ilike', '%unit%')], context=context)
        if not product_uom_ids:
            # No se encuentra unidad de medida para poner por defecto, se usa "1"
            values['uom_id'] = 1
        else:
            values['uom_id'] = product_uom_ids[0]
        line_sr_obj = self.pool.get('grp.compras.solicitud.recursos.line.sr')
        new_line_sr = line_sr_obj.create(cr, uid, values, context=context)
        if not new_line_sr:
            return False
        else:
            return True

    # agregado compras grp
    def copy(self, cr, uid, id, default=None, context=None):
        default = default or {}
        line_sr_obj = self.pool.get('grp.compras.solicitud.recursos.line.sr')
        r = self.browse(cr, uid, id)
        lines = []
        for line in r.sr_id.grp_sr_id:
            l_new = line_sr_obj.copy(cr, uid, line.id, default={})
            lines.append(l_new)
        default.update({
            'name': u'SR-Borrador',
            'grp_sr_id': [(6, 0, lines)]
        })
        id_sr_alm = super(grp_compras_solicitud_recursos_almacen, self).copy(cr, uid, id, default, context)
        id_lines = []
        sr_almacen = self.browse(cr, uid, id_sr_alm, context=context)
        for line_sr in sr_almacen.sr_id.grp_sr_id:
            id_lines.append(line_sr.id)
        if id_lines:
            line_sr_obj.write(cr, SUPERUSER_ID, id_lines,
                              {'cantidad_pedida': 0, 'cantidad_en_pedido': 0, 'cantidad_entregada': 0,
                               'state': 'inicio'})
        return id_sr_alm

    def button_cumplido_af(self, cr, uid, ids, context=None):
        pool_asset = self.pool.get('account.asset.asset')
        pool_historia = self.pool.get('grp.historial_responsable')
        for rec in self.browse(cr, uid, ids, context=context):
            #diccionario para guardar cantidades por cada producto
            dict_prod_cant = {}
            list_af = [l.articulo_af.numero_activo for l in rec.grp_sr_af_id if l.articulo_af
                       and l.articulo_af.numero_activo]
            list_af_2 = list(set(list_af))
            if len(list_af_2) < len(list_af):
                raise ValidationError(u"No es posible ingresar dos o más líneas con el mismo Artículo AF. "
                                      u"Por favor, elimine los repetidos.")
            for line_af in rec.grp_sr_af_id:
                if not line_af.product_id:
                    raise ValidationError(u"Debe ingresar un Producto en las líneas de AF.")
                if not line_af.articulo_af:
                    raise ValidationError(u"Debe ingresar un Artículo AF en las líneas de AF.")
                if not line_af.ubicacion_origen:
                    raise ValidationError(u"Debe ingresar una Ubicación de origen en las líneas de AF.")
                if not line_af.responsable_actual:
                    raise ValidationError(u"Debe ingresar un Responsable en las líneas de AF.")
                # HACK
                if hasattr(line_af, 'ubicacion_fisica') and not line_af.ubicacion_fisica:
                    raise ValidationError(u"Debe ingresar una Ubicación física en las líneas de AF.")
                ##
                if line_af.articulo_af.product_id:
                    if line_af.product_id.id != line_af.articulo_af.product_id.id:
                        raise ValidationError(u"Debe ingresar un AF cuyo producto sea el mismo que el ingresado en"
                                              u" la línea de la SR.")
                else:
                    raise ValidationError(u"Debe ingresar un AF cuyo producto sea el mismo que el ingresado en"
                                              u" la línea de la SR.")
                articulo = line_af.articulo_af.id
                vals = {
                    'product_id': line_af.product_id.id,
                    'department_id': line_af.ubicacion_origen.id,
                    'user_id': line_af.responsable_actual.id,
                }
                if hasattr(line_af, 'ubicacion_fisica'):
                    vals.update({'ubicacion_fisica': line_af.ubicacion_fisica.id})
                ctx = context.copy()
                ctx = dict(ctx)
                ctx.update({'doc_origin': rec.id,
                            'restrict_lot_ids':
                                {articulo: line_af.restrict_lot_id.id}
                            })
                pool_asset.write(cr, uid, [articulo], vals, context=ctx)
                #actualizo el diccionario de cantidades por producto
                key = line_af.product_id.id
                if not key in dict_prod_cant:
                    dict_prod_cant[key] = 1
                else:
                    dict_prod_cant[key] += 1
            #Actualizo estado de las lineas segun lo que tengo para entregar
            for line_sr in rec.grp_sr_id:
                if line_sr.product_id.id in dict_prod_cant:
                    #si la cantidad coincide la dejo en 0 y actualizo
                    if line_sr.cantidad_solicitada == dict_prod_cant[line_sr.product_id.id]:
                        line_sr.write({'cantidad_entregada': line_sr.cantidad_solicitada})
                        dict_prod_cant[line_sr.product_id.id] = 0
                    #si tengo mas de lo que solicite, entrego y resto esa cantidad
                    elif line_sr.cantidad_solicitada < dict_prod_cant[line_sr.product_id.id]:
                        line_sr.write({'cantidad_entregada': line_sr.cantidad_solicitada})
                        dict_prod_cant[line_sr.product_id.id] -= line_sr.cantidad_solicitada
                    #si no me da para entregar completo entrego lo que tengo
                    else:
                        line_sr.write({'cantidad_entregada': dict_prod_cant[line_sr.product_id.id]})
                        dict_prod_cant[line_sr.product_id.id] = 0

            wf_service = netsvc.LocalService('workflow')
            wf_service.trg_validate(uid, 'grp.compras.solicitud.recursos.almacen', rec.id, 'button_wkf_sr_cerrar_sr_almacen', cr)
        return True


class grp_compras_solicitud_recursos_line_sr(osv.osv):
    _name = 'grp.compras.solicitud.recursos.line.sr'
    _description = 'Lineas de Solicitud de Recurso'
    _rec_name = 'product_id'

    def fields_get(self, cr, uid, allfields=None, context=None, write_access=True, attributes=None):
        res = super(grp_compras_solicitud_recursos_line_sr, self).fields_get(cr, uid, allfields=allfields, context=context, write_access=write_access, attributes=attributes)
        if not self.pool.get('res.users').has_group(cr, uid,
                                                    'grp_seguridad.grp_compras_sr_Solicitante') and not self.pool.get(
            'res.users').has_group(cr, uid, 'grp_seguridad.grp_compras_sr_Aprobador'):
            res['descripcion']['readonly'] = True
        return res

    LISTA_ESTADOS_LINEA_SOLICITUD = [
        ('noe', 'No entregado'),
        ('noh', 'No hay'),
        ('parcial', 'Entregado Parcial'),
        ('total', 'Entregado Total'),
        ('enaprobcom', 'En aprobacion compras'),
        ('acompra', 'Enviado a compras'),
        ('rechazado', 'Rechazado por Compras'),
    ]

    def onchange_product_id(self, cr, uid, ids, product_id):
        value = {}
        if product_id:
            prod = self.pool.get('product.product').browse(cr, uid, product_id)
            if prod.product_tmpl_id.id:
                prod_uom_id = prod.product_tmpl_id.uom_id.id or prod.uom_id.id
                value = {'precio': prod.product_tmpl_id.standard_price,
                         'uom_id': prod_uom_id}
                # if prod.grp_sice_cod:
                #     pool_art_serv_obra = self.pool.get('grp.sice_art_serv_obra')
                #     pool_uom = self.pool.get('product.uom')
                #     sice_cod = prod.grp_sice_cod
                #     art_id = pool_art_serv_obra.search(cr, uid, [('cod', '=', sice_cod)])
                #     if len(art_id) > 0:
                #         art_id = art_id[0]
                #     art_obj = pool_art_serv_obra.browse(cr, uid, art_id)
                #     uom_ids = [prod_uom_id]
                #     for uom in art_obj.unidades_med_ids:
                #         prod_uom = pool_uom.search(cr, uid, [('sice_uom_id', '=', uom.id)])
                #         if len(prod_uom) > 0:
                #             prod_uom = prod_uom[0]
                #         prod_uom_obj = pool_uom.browse(cr, uid, prod_uom)
                #         if prod_uom and prod_uom_obj.category_id.id == prod.product_tmpl_id.uom_id.category_id.id:
                #             uom_ids.append(prod_uom)
                #     domain = {
                #         'uom_id': str([('id', 'in', uom_ids)])
                #     }
                #     return {'value': value}
        return {'value': value}

    def _domain_sc(self, cr, uid, ids, d1, d2, context=None):
        res = {}
        for lines in self.browse(cr, uid, ids, context=None):
            res[lines.id] = lines.cantidad_solicitada - lines.cantidad_pedida - lines.cantidad_entregada > 0
        return res

    def _domain_solicitante(self, cr, uid, ids, d1, d2, context=None):
        in_grp = self.pool.get('res.users').has_group(cr, uid, 'grp_seguridad.grp_compras_sr_Solicitante')
        res = {}
        for lines in self.browse(cr, uid, ids, context=None):
            res[lines.id] = in_grp and lines.grp_id.state in ['inicio', 'nuevo']
        return res

    def _domain_aprobador(self, cr, uid, ids, d1, d2, context=None):
        in_grp = self.pool.get('res.users').has_group(cr, uid, 'grp_seguridad.grp_compras_sr_Aprobador')
        res = {}
        for lines in self.browse(cr, uid, ids, context=None):
            res[lines.id] = (in_grp and lines.grp_id.state in ['en_aprobacion']) or (
                in_grp and lines.estado in ['enaprobcom'])
        return res

    def _domain_almacenero(self, cr, uid, ids, d1, d2, context=None):
        in_grp = self.pool.get('res.users').has_group(cr, uid,
                                                      'grp_seguridad.grp_compras_sr_Encargado_de_almacen')
        res = {}
        for lines in self.browse(cr, uid, ids, context=None):
            # res[lines.id] = in_grp and lines.grp_id.state in ['codificando']
            res[lines.id] = in_grp and lines.grp_id.state in ['codificando']
        return res

    def _domain_product(self, cr, uid, ids, d1, d2, context=None):
        res = {}
        for lines in self.browse(cr, uid, ids, context=None):
            res[lines.id] = lines.grp_id.state not in ['nuevo,inicio,en_aprobacion,esperando_almacen']
        return res

    def get_estado_linea(self, cr, uid, ids, fieldname, args, context=None):
        res = {}
        for lines in self.browse(cr, uid, ids, context=context):
            if lines.boton_check:
                res[lines.id] = 'enaprobcom'
            elif lines.cantidad_solicitada == lines.cantidad_entregada:
                res[lines.id] = 'total'
            elif lines.cantidad_entregada > 0:
                res[lines.id] = 'parcial'
            # Falta un estado
            elif lines.cantidad_en_pedido > 0:
                res[lines.id] = 'acompra'
            else:
                res[lines.id] = 'noe'
                # TODO dar opciones para que no se entregue o no haya
        return res

    def _pendiente(self, cr, uid, ids, prop, unknow_none, unknow_dict):
        res = {}
        for line in self.browse(cr, uid, ids):
            pendiente = line.cantidad_solicitada - line.cantidad_entregada
            res[line.id] = pendiente
        return res

    LISTA_ESTADOS_SOLICITUD = [
        ('inicio', 'Borrador'),
        ('en_aprobacion', u'En aprobación'),
        ('rechazado', 'Rechazado'),
        ('codificando', u'Aprobado'),
        ('esperando_almacen', u'En Proceso'),
        ('aprobado', 'Cerrado'),
    ]

    LISTA_TIPO_SR_ALMACEN_REL = [
        ('I', 'Insumos/Materiales'),
        ('S', 'Servicios'),
        ('AF', 'Activo Fijo'),
        ('PL', 'Planificada')
    ]

    TIPO_ESTADO_PROCESO = [
        ('eprocalm', u'En Proceso Almacenero'),
        ('eaprobcomp', u'En Aprobación Compras'),
        ('envcomp', u'Enviado a Compras'),
        ('pendrecep', u'Pendiente Recepción'),
    ]


    def _get_estado_en_proc(self, cr, uid, ids, name, args, context=None):
        res = {}
        sr_alm_obj = self.pool.get('grp.compras.solicitud.recursos.almacen')
        for rec in self.browse(cr, uid, ids, context=context):
            res[rec.id] = False
            if rec.grp_id:
                sr_id = sr_alm_obj.search(cr, uid, [('sr_id', '=', rec.grp_id.id)], context=context)
                if sr_id:
                    sr_alm = sr_alm_obj.browse(cr, uid, sr_id)
                    res[rec.id] = sr_alm.estado_en_proc
        return res


    _columns = {
        'grp_id': fields.many2one('grp.compras.solicitud.recursos', 'Solicitud', ondelete='cascade'),

        'product_id': fields.many2one('product.product', 'Producto'),
        'uom_id': fields.many2one('product.uom', string='UdM', ondelete='restrict'),
        'descripcion': fields.char(u'Descripción', size=250, required=True),

        'cantidad_solicitada': fields.float('Cantidad', digits_compute=dp.get_precision('Cantidad'), required=True),
        'cantidad_en_pedido': fields.float('En pedido', digits_compute=dp.get_precision('Cantidad'), required=True),
        'cantidad_entregada': fields.float('Cantidad Entregada', digits_compute=dp.get_precision('Cantidad')),
        'estado': fields.function(get_estado_linea, type='selection', selection=LISTA_ESTADOS_LINEA_SOLICITUD,
                                  string='Estado', store=True),
        'cantidad_pedida': fields.float('Cantidad a pedir', digits_compute=dp.get_precision('Cantidad')),
        'domain_sc': fields.function(_domain_sc, type='boolean', store=True),
        'domain_solicitante': fields.function(_domain_solicitante, type='boolean', store=False),
        'domain_aprobador': fields.function(_domain_aprobador, type='boolean', store=False),
        'domain_almacenero': fields.function(_domain_almacenero, type='boolean', store=False),
        'domain_product': fields.function(_domain_product, type='boolean', store=False),
        'cantidad_pendiente': fields.function(_pendiente, string='Cantidad pendiente', type='float',
                                              digits_compute=dp.get_precision('Account')),
        # campos para vista tree Listado SR por Solicitante
        'nro_solicitud': fields.related('grp_id', 'name', string='Nro. Solicitud', type='char'),
        'fecha_solicitud': fields.related('grp_id', 'date_start', string='Fecha de Solicitud', type='date'),
        'description': fields.related('grp_id', 'description', type='text', string=u'Descripción'),
        'solicitante_id': fields.related('grp_id', 'solicitante_id', type='many2one', relation='res.users',
                                         string='Solicitante', store=True),
        'department_id': fields.related('grp_id', 'department_id', type='many2one', relation='hr.department',
                                       string='Departamento', store=True),
        'estado_en_proc': fields.function(_get_estado_en_proc, type='selection', selection=TIPO_ESTADO_PROCESO,
                                          string="Estado en proceso"),
        'fecha_necesidad': fields.date('Fecha de necesidad'),
        'boton_check': fields.boolean(u'Botón pulsado'),
        'monto': fields.float('Monto'),
        'moneda': fields.many2one('res.currency', 'Moneda'),
        'cuenta_analitica': fields.many2one('account.analytic.account', u'Cuenta analítica'),
        'cuenta_contable': fields.many2one('account.account', u'Cuenta contable'),
        'disponible': fields.char('Disponible', size=64),
    }

    _defaults = {
        'boton_check': False,
        'cantidad_pedida': 0,
        'cantidad_solicitada': 1,
        'cantidad_en_pedido': 0,
        'cantidad_pendiente': 0,
        'domain_solicitante': True,
        'domain_almacenero': False,
        'domain_aprobador': False,
    }

class grp_compras_solicitud_recursos_line_sr_af(osv.osv):
    _name = 'grp.compras.solicitud.recursos.line.sr.af'
    _description = 'Lineas de sr Activo fijo'
    _columns = {
        'product_id': fields.many2one('product.product', 'Producto'),
        'grp_id': fields.many2one('grp.compras.solicitud.recursos.almacen', 'Solicitud', ondelete='cascade'),

        'articulo_af': fields.many2one('account.asset.asset', u'Artículo AF'),
        'ubicacion_origen': fields.many2one('hr.department', u'Ubicación'),
        'responsable_actual': fields.many2one('res.users',u'Responsable'),
        'estado_aprob_af': fields.related('articulo_af', 'estado_responsable', string='Estado de aprobación del AF',
                                          type='selection', selection=_ESTADO_HISTORIAL_RESP),
    }

LISTA_ESTADOS_SOLICITUD = [
    ('noe', 'No entregado'),
    ('noh', 'No hay'),
    ('parcial', 'Entregado Parcial'),
    ('total', 'Entregado Total'),
    ('enaprobcom', u'En aprobación compras'),
    ('acompra', 'Enviado a compras'),
    ('rechazado', 'Rechazado por Compras'),
]


class solicitud_recursos_line_list(osv.osv):
    _name = "grp.compras.sr.lines.transacciones"
    _description = "Listado de Transacciones Unificadas SR"
    _order = "id asc"
    _auto = False
    _columns = {
        'id': fields.integer('Id', readonly=True),
        'product_id': fields.many2one('product.product', 'Producto', required=True, select=True),
        'uom_id': fields.many2one('product.uom', 'Unidad de medida', required=True),
        'cantidad_solicitada': fields.float('Cantidad solicitada',
                                            digits_compute=dp.get_precision('Product Unit of Measure')),
        'cantidad_entregada': fields.float('Cantidad entregada',
                                           digits_compute=dp.get_precision('Product Unit of Measure')),
        'cantidad_pendiente': fields.float('Cantidad pendiente',
                                           digits_compute=dp.get_precision('Product Unit of Measure')),
        'sr_id': fields.many2one('grp.compras.solicitud.recursos', u'Nº SR', ondelete='set null'),
        'sc_id': fields.many2one('grp.solicitud.compra', u'Nº SC', ondelete='set null'),
        'pedido_compra_id': fields.many2one('grp.pedido.compra', u'Nº PC', ondelete='set null'),
        'order_id': fields.many2one('purchase.order', u'Nº OC', ondelete='set null'),
        'estado': fields.selection(LISTA_ESTADOS_SOLICITUD, string='Estado', select=True),
        'descripcion': fields.char(u'Descripción', size=64, select=True),
        'state': fields.char('Estado',size=20),
        'department_id': fields.many2one('hr.department', string=u'Departamento', select=True),
        'operating_unit_id': fields.many2one('operating.unit', string=u'UE', select=True),
        'date_start': fields.date(string='Fecha de Solicitud'),

    }

    def init(self, cr):
        drop_view_if_exists(cr, 'grp_compras_sr_lines_transacciones')
        cr.execute("""
         create or replace view grp_compras_sr_lines_transacciones as (
         SELECT ROW_NUMBER() over() as id, lsr.product_id, puom.id as uom_id, lsr.cantidad_solicitada, lsr.cantidad_entregada,
            (COALESCE(lsr.cantidad_solicitada,0) - COALESCE(lsr.cantidad_entregada,0)) as cantidad_pendiente,
            lsr.estado,lsr.descripcion, sr.name,
            sr.id as sr_id,sc.id as sc_id,
            pc.id as pedido_compra_id,
            ocl.order_id,
            sr.state,
            sr.department_id,
            sra.operating_unit_id as operating_unit_id,
            sr.date_start
            from grp_compras_solicitud_recursos_line_sr lsr
            left outer join product_product p on p.id = lsr.product_id
            left outer join product_template pt on pt.id = p.product_tmpl_id
            left outer join product_uom puom on puom.id = pt.uom_id
            left outer join grp_compras_solicitud_recursos sr on lsr.grp_id = sr.id
            left outer join grp_compras_solicitud_recursos_almacen sra on sra.sr_id = sr.id
            left outer join grp_solicitud_compra sc on lsr.id = sc.linea_solicitud_recursos_id
            left outer join grp_linea_pedido_compra lpc on lpc.solicitud_compra_id = sc.id
            left outer join grp_pedido_compra pc on pc.id = lpc.pedido_compra_id
            left outer join purchase_order oc on oc.pedido_compra_id = pc.id
            left outer join purchase_order_line ocl on ocl.order_id = oc.id and ocl.product_id = p.id
            WHERE sr.state <> 'inicio'
            ORDER BY id asc)""")

    def open_sr(self, cr, uid, ids, context=None):
        sr_alm_obj = self.pool.get('grp.compras.solicitud.recursos.almacen')
        for linea in self.browse(cr, uid, ids, context=context):
            if linea.sr_id:
                sr_id = sr_alm_obj.search(cr, uid, [('sr_id', '=', linea.sr_id.id)], context=context)
                if sr_id:
                    return {
                        'type': 'ir.actions.act_window',
                        'view_type': 'form',
                        'view_mode': 'form',
                        'res_model': 'grp.compras.solicitud.recursos.almacen',
                        'res_id': sr_id and sr_id[0],
                        'target': 'new',
                        'context': context,
                    }

    def open_sc(self, cr, uid, ids, context=None):
        for linea in self.browse(cr, uid, ids, context=context):
            if linea.sc_id:
                return {
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'grp.solicitud.compra',
                    'res_id': linea.sc_id.id,
                    'target': 'new',
                    'context': context,
                }

    def open_pdc(self, cr, uid, ids, context=None):
        for linea in self.browse(cr, uid, ids, context=context):
            if linea.pedido_compra_id:
                return {
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'grp.pedido.compra',
                    'res_id': linea.pedido_compra_id.id,
                    'target': 'new',
                    'context': context,
                }

    def open_oc(self, cr, uid, ids, context=None):
        for linea in self.browse(cr, uid, ids, context=context):
            if linea.order_id:
                return {
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'purchase.order',
                    'res_id': linea.order_id.id,
                    'target': 'new',
                    'context': context,
                }

class grp_fecha_planificada(osv.osv):
    _name = 'grp.fecha.planificada'

    def _get_years(self, cr, uid, context=None):
        current_year = datetime.date.today().year
        select = [(str(year),str(year)) for year in range(current_year, current_year+5)]
        select.reverse()
        return select

    _columns = {
        'year': fields.selection(_get_years, string=u'Año', required=True, default=str(datetime.date.today().year)),
        'reception_date': fields.date(u'Fecha recepción', required=True)
    }
    _sql_constraints = [
        ('year_planif_uniq', 'unique(year)', 'Debe existir una sola fecha configurada por cada año'),
    ]
