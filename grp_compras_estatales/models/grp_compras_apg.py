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
import time
from lxml import etree
from openerp import SUPERUSER_ID
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from datetime import date, datetime, timedelta
import logging
_logger = logging.getLogger(__name__)


# ================================================================
#       Autorización para gastar
# ================================================================

class grp_compras_apg(osv.osv):
    _name = 'grp.compras.apg'
    _inherit = ['mail.thread']
    _description = u'Autorización para gastar'
    _order = 'id desc'

    LISTA_ESTADO_APG = [
        ('nuevo', 'Borrador'),
        ('en_financiero', 'En financiero'),
        ('afectado', 'Afectada'),
        ('desafectado', 'Anulada en SIIF'),
        ('anulada', 'Anulada'),
    ]

    def _get_totales(self, cr, uid, ids, fieldname, args, context=None):
        res = {}
        ctx = {}
        currency_obj = self.pool.get('res.currency')
        for apg in self.browse(cr, uid, ids, context=context):
            #calculo el importe divisa
            total = 0.0
            for linea in apg.lprapg_ids:
                total += linea.subtotal_divisa
            #calculo el importe en moneda base
            moneda_base = apg.company_id.currency_id and apg.company_id.currency_id.id
            if apg.moneda.id != moneda_base:
                ctx.update({'date': apg.fecha_tipo_cambio or time.strftime('%Y-%m-%d'), 'pricelist_type': 'presupuesto'})
                total_estimado = currency_obj.compute(cr, uid, apg.moneda.id, moneda_base, total, context=ctx)
            else:
                total_estimado = total
            res[apg.id] = {
                'total_importe_divisa': total,
                'total_estimado': round(total_estimado),
            }
        return res

    def _get_moneda(self, cr, uid, context=None):
        res = self.pool.get('res.users').read(cr, uid, [uid], ['company_id'], context=context)
        if res and res[0]['company_id']:
            company_id = res[0]['company_id'][0]
        else:
            return False
        res = self.pool.get('res.company').read(cr, uid, [company_id], ['currency_id'], context=context)
        if res and res[0]['currency_id']:
            currency_id = res[0]['currency_id'][0]
        else:
            return False
        return currency_id

    # def _get_odg_editable(self, cr, uid, ids, name, args, context=None):
    #     res = {}
    #     in_grp = self.pool.get('res.users').has_group(cr, uid, 'grp_seguridad.grp_compras_apg_Jefe_de_compras')
    #     for record in self.browse(cr, uid, ids, context=context):
    #         res[record.id] = (record.state in ('en_aprobacion', 'aprobado', 'en_autorizacion_ODG')) and in_grp
    #     return res

    def _get_default_editable(self, cr, uid, ids, name, args, context=None):
        res = {}
        in_grp = self.pool.get('res.users').has_group(cr, uid, 'grp_seguridad.grp_compras_apg_Comprador')
        for record in self.browse(cr, uid, ids, context=context):
            res[record.id] = (record.state in ('nuevo')) and in_grp
        return res

    def _get_responsable_siif_editable(self, cr, uid, ids, name, args, context=None):
        res = {}
        in_grp = self.pool.get('res.users').has_group(cr, uid, 'grp_seguridad.grp_compras_apg_Responsable_SIIF')
        for record in self.browse(cr, uid, ids, context=context):  # incidencia 013 Inicio y fin
            res[record.id] = (record.state in ('nuevo', 'desafectado')) and in_grp
        return res

    # 012 - Inicio
    def _get_gesto_pasajes_editable(self, cr, uid, ids, name, args, context=None):
        res = {}
        in_gp = self.pool.get('res.users').has_group(cr, uid, 'grp_seguridad.grp_compras_apg_Gestor_pasajes')
        in_jc = self.pool.get('res.users').has_group(cr, uid, 'grp_seguridad.grp_compras_apg_Jefe_de_compras')
        for record in self.browse(cr, uid, ids, context=context):
            res[record.id] = in_jc or in_gp
        return res

    def _get_tipo_de_cambio_fnc(self, cr, uid, ids, fieldname, args, context=None):
        res = {}
        for lines in self.browse(cr, uid, ids, context=context):
            res[lines.id] = lines.tipo_de_cambio
        return res

    def _get_monto_fnc(self, cr, uid, ids, fieldname, args, context=None):
        if context is None:
            context = {}
        context = dict(context)
        res = {}
        currency_obj = self.pool.get('res.currency')
        for lines in self.browse(cr, uid, ids, context=context):
            importe_mbase = lines.monto_divisa
            if lines.moneda.id != lines.company_currency_id.id:
                context.update({'pricelist_type': 'presupuesto', 'date': lines.fecha_tipo_cambio})
                importe_mbase = currency_obj.compute(cr, uid, lines.moneda.id, lines.company_currency_id.id,
                                                     lines.monto_divisa, context=context)
            res[lines.id] = round(importe_mbase)
        return res

    def _get_diferente(self, cr, uid, ids, field_name, args, context=None):
        result = {}
        for compras_apg in self.browse(cr, uid, ids, context):
            result[compras_apg.id] = False
            if compras_apg.moneda != compras_apg.company_currency_id:
                result[compras_apg.id] = True
        return result

    # 022 Incidencia reporte apg
    def _get_numero_oc(self, cr, uid, ids, field_name, args, context=None):
        result = {}
        for compras_apg in self.browse(cr, uid, ids, context):
            result[compras_apg.id] = False
            if compras_apg.pc_id:
                nombre = compras_apg.pc_id.name
                short_name = nombre[-5:]
                result[compras_apg.id] = int(short_name)
        return result

    # # 016 Inicio
    # def _pc_origen_fondo_rotatorio(self, cr, uid, ids, name, arg, context=None):
    #     res = {}
    #     for apg in self.browse(cr, uid, ids, context=context):
    #         # fondo_rotatorio  devolver siempre false
    #         # res[apg.id] = (True and apg.fondo_rotatorio or apg.pc_id.tipo_proc_corto and apg.pc_id.tipo_proc_corto == 'fondo_rot') or False
    #         res[apg.id] = False
    #     return res

    # ODG_SELECTION = [
    #     ('prim', 'Primario'),
    #     ('sec', 'Secundario'),
    # ]

    _columns = {
        'pc_id': fields.many2one('grp.pedido.compra', 'Documento origen', help='Documento origen', ondelete='restrict'),
        'lprapg_ids': fields.one2many('grp.compras.apg.lineas.resumen', 'apg_id', string=u'Líneas de pedido resumen'),
        # , ondelete = 'cascade' ),
        'name': fields.char(u'Nro. APG', required=True, help=u'Nro. de la APG'),  # secuencia
        'sice_nro': fields.related('pc_id', 'sice_id_compra', type='integer'),
        'nro_ampliacion': fields.related('pc_id', 'nro_ampliacion', type='integer', string=u'N° Ampliación',
                                         help=u'Número de Ampliación'),
        # 019 Incidencia nro ampliacion
        'origen_es_ampliacion': fields.related('pc_id', 'ampliacion', type='boolean', string=u'Es ampliacion',
                                               help=u'PC es Ampliación'),
        # 019 Incidencia nro ampliacion
        'nro_adj': fields.char(u'Nro. de Adjudicación', size=20),
        'descripcion': fields.text(u'Descripción', size=250),
        'moneda': fields.many2one('res.currency', 'Divisa', required=True),
        'company_currency_id': fields.many2one('res.currency', 'Moneda empresa', required=True),
        'tipo_de_compra': fields.related('pc_id', 'tipo_compra', type='many2one', relation='sicec.tipo.compra',
                                         readonly=True, string='Tipo de compra', store=True),
        'sub_tipo_compra': fields.related('pc_id', 'sub_tipo_compra', type='many2one', relation='sicec.subtipo.compra',
                                          readonly=True, string='Sub tipo compra'),
        # incidencia mejora 07/07
        'monto': fields.integer(u'Equivalente en pesos'),
        # digits = (10,2)), #'Monto a autorizar pesos' cambiado 06/05   cambiado a entero 21/10
        'monto_fnc': fields.function(_get_monto_fnc, string=u'Equivalente en pesos'),
        # type='integer', digits=(10, 0)), #'Monto a autorizar pesos' cambiado 06/05
        'monto_divisa': fields.float('Monto a autorizar divisa', digits_compute=dp.get_precision('Account')),  # digits = ( 10, 0 ) ),
        'state': fields.selection(LISTA_ESTADO_APG, string=u'Estado', track_visibility='onchange'),
        'fecha': fields.date('Fecha', required=True),
        'fecha_tipo_cambio': fields.date('Fecha tipo de cambio'),
        'tipo_de_cambio': fields.float('Tipo de cambio', digits=(10, 5)),
        'tipo_de_cambio_fnc': fields.function(_get_tipo_de_cambio_fnc, string='Tipo de cambio', type='float',
                                              digits=(10, 5)),
        'diferente_divisa': fields.function(_get_diferente, string='Diferencia moneda', type='boolean'),
        'nro_afectacion_siif': fields.integer(u'Nro Afectación SIIF', help=u'Nro. de afectación SIIF'),
        # 011- #Nro Afectación incidencia cambiar label
        'responsable_siif_editable': fields.function(_get_responsable_siif_editable, type='boolean', store=False),
        'gestor_pasaje': fields.function(_get_gesto_pasajes_editable, type='boolean'),
        # 'odg': fields.many2one('res.users', 'Ordenador del gasto', help='Ordenador del gasto'),
        'no_pedido_oc': fields.function(_get_numero_oc, string='Numero oc', type='char'),
        'total_estimado': fields.function(_get_totales, multi='totales', string='Total estimado pesos', type='float',
                                          digits=(16, 0)),
        # digits_compute=dp.get_precision ( 'Cantidad' ) ),
        'total_importe_divisa': fields.function(_get_totales, multi='totales', string='Total estimado divisa', type='float',
                                                digits_compute=dp.get_precision('Account')),  # digits_compute=dp.get_precision ( 'Cantidad' ) ),
        # 'odg_editable': fields.function(_get_odg_editable, type='boolean', store=False),
        'default_editable': fields.function(_get_default_editable, type='boolean', store=False),
        'company_id': fields.many2one('res.company', u'Compañía', required=True),
        'purchase_order_ids': fields.one2many('purchase.order', 'pc_apg_id', 'Ordenes de compra'),
        # 'tipo_odg': fields.selection(ODG_SELECTION, 'Tipo de ODG'),
    }

    # def onchange_odg(self, cr, uid, ids, odg):
    #     if odg:
    #         usr_obj = self.pool.get('res.users')
    #         es_ord_prim = usr_obj.has_group(cr, odg,
    #                                         'grp_seguridad.grp_compras_apg_Ordenador_del_gasto_primario')
    #         if es_ord_prim:
    #             return {'value': {'tipo_odg': 'prim'}}
    #         else:
    #             return {'value': {'tipo_odg': 'sec'}}
    #     else:
    #         return {}

    _defaults = {
        'name': 'Inicial',
        'state': 'nuevo',
        'moneda': _get_moneda,  # Moneda de la empresa
        'company_currency_id': _get_moneda,  # Moneda de la empresa
        'fecha_tipo_cambio': time.strftime('%Y-%m-%d'),
        'company_id': lambda self, cr, uid, c: self.pool.get('res.users').browse(cr, SUPERUSER_ID, uid,
                                                                                 c).company_id.id,
    }

    # def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
    #     if context is None:
    #         context = {}
    #     res = super(grp_compras_apg, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type,
    #                                                        context=context,
    #                                                        toolbar=toolbar, submenu=submenu)
    #     model_data_obj = self.pool.get('ir.model.data')
    #     res_groups_obj = self.pool.get('res.groups')
    #     group_verifier_id = model_data_obj._get_id(cr, uid, 'grp_seguridad',
    #                                                'grp_compras_apg_Ordenador_del_gasto')
    #     domain_user = False
    #     if group_verifier_id:
    #         res_id = model_data_obj.read(cr, uid, [group_verifier_id], ['res_id'])[0]['res_id']
    #         group_verifier = res_groups_obj.browse(cr, uid, res_id, context=context)
    #         group_user_ids = [user.id for user in group_verifier.users]
    #         domain_user = str([('id', 'in', group_user_ids)])
    #     if domain_user:
    #         doc = etree.XML(res['arch'])
    #         for node in doc.xpath("//field[@name='odg']"):
    #             node.set('domain', domain_user)
    #         res['arch'] = etree.tostring(doc)
    #     return res

    def unlink(self, cr, uid, ids, context=None):
        apg = self.read(cr, uid, ids, ['state', 'name'], context=context)
        unlink_ids = []
        for s in apg:
            if s['state'] in ['nuevo']:
                unlink_ids.append(s['id'])
            else:
                if len(ids) > 1:
                    raise osv.except_osv(_('Acción inválida!'),
                                         _('Solamente puede eliminar un APG en estado Borrador.'))
                else:
                    estado = s['state']
                    name = s['name']
                    for list_item in self.LISTA_ESTADO_APG:
                        if list_item[0] == s['state']:
                            estado = list_item[1]
                            break
                    raise osv.except_osv(_(u'Acción inválida!'),
                                         _(u'La APG %s no se puede eliminar porque está en estado %s.') % (
                                             name, estado,))
        return super(grp_compras_apg, self).unlink(cr, uid, unlink_ids, context=context)

    def onchange_date_currency_id_apg(self, cr, uid, ids, moneda, fecha, company_currency_id, monto_divisa=False):
        context = {}
        currency_obj = self.pool.get('res.currency')
        context = dict(context)
        if not moneda:
            return {'value': {'tipo_de_cambio': False}}
        if fecha:
            context.update({'date': fecha})
        else:
            context.update({'date': time.strftime('%Y-%m-%d')})
        currency = self.pool.get('res.currency').browse(cr, uid, moneda, context=context)
        rate = currency.rate_presupuesto  # cambio 17/11
        importe_mbase = monto_divisa
        if moneda != company_currency_id:
            context.update({'pricelist_type': 'presupuesto'})
            importe_mbase = currency_obj.compute(cr, uid, moneda, company_currency_id, monto_divisa, context=context)

        return {'value': {'tipo_de_cambio': rate,
                          'tipo_de_cambio_fnc': rate,
                          'diferente_divisa': moneda != company_currency_id,
                          'monto_fnc': round(importe_mbase),  # redondear importe moneda base 21/10
                          'monto_divisa': monto_divisa,
                          'monto': round(importe_mbase)}}  # redondear el importe 21/10

    # workflow
    # actividades: se ejecutan las funciones al 'llegar' el flujo a la actividad (estado)

    # def act_apg_inicio(self, cr, uid, ids, context=None):
    #     for r in self.browse(cr, uid, ids, context=context):
    #         self.write(cr, uid, [r.id], {'state': 'inicio'}, context=context)
    #     return True

    # # al pasar el estado a 'nuevo' se asigna nuevo número de APG
    # def act_apg_nuevo(self, cr, uid, ids, context=None):
    #     values = {}
    #     for r in self.browse(cr, uid, ids, context=context):
    #         values['state'] = 'nuevo'
    #         self.write(cr, uid, [r.id], values, context=context)
    #     return True

    # TODO Spring 6 GAP 123
    def act_apg_en_financiero(self, cr, uid, ids, context=None):
        for r in self.browse(cr, uid, ids, context=context):
            if r.monto_divisa <= 0:
                raise osv.except_osv('Error!', u'El monto a autorizar debe ser mayor a 0')
            to_update = {'state': 'en_financiero'}
            # to_update['name'] = self.pool.get('ir.sequence').get(cr, uid, 'apg.nroapg', context=context)
            sequence = self.pool.get('ir.sequence').get(cr, uid, 'apg.nroapg', context=context)
            ind= sequence.index('-') +1
            to_update['name'] = sequence[0:ind] + r.company_id.inciso + sequence[ind:len(sequence)]
            self.write(cr, uid, [r.id], to_update, context=context)
        return True

    # def act_apg_en_aprobacion(self, cr, uid, ids, context=None):
    #     if context is None:
    #         context = {}
    #     context = dict(context)
    #     for r in self.browse(cr, uid, ids, context=context):
    #         to_update = {'state': 'en_aprobacion'}
    #         to_update['name'] = self.pool.get('ir.sequence').get(cr, uid, 'apg.nroapg', context=context)
    #         self.write(cr, uid, [r.id], to_update, context=context)
    #     return True
    #
    # def act_apg_aprobado(self, cr, uid, ids, context=None):
    #     for r in self.browse(cr, uid, ids, context=context):
    #         self.write(cr, uid, [r.id], {'state': 'aprobado'}, context=context)
    #     return True
    #
    # def act_apg_en_autorizacion_ODG(self, cr, uid, ids, context=None):
    #     for r in self.browse(cr, uid, ids, context=context):
    #         self.write(cr, uid, [r.id], {'state': 'en_autorizacion_ODG'}, context=context)
    #     return True
    #
    # def act_apg_autorizado_ODG(self, cr, uid, ids, context=None):
    #     for r in self.browse(cr, uid, ids, context=context):
    #         self.write(cr, uid, [r.id], {'state': 'autorizado_ODG', 'odg': uid}, context=context)
    #     return True

    # nuevo estado de workflow, estado final
    def act_apg_anular(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'anulada'}, context=context)
        return True

    def act_apg_afectado(self, cr, uid, ids, context=None):
        for r in self.browse(cr, uid, ids, context=context):
            # PCAR 11 08 2017 inicio Actualizar flag apg_afectada en pc_id si cumple las condiciones
            pc_fecha_creacion = r.pc_id.date_start
            anio = datetime.strptime(pc_fecha_creacion, "%Y-%m-%d").date().year
            apg_anio_fiscal = int(r.fiscalyear_siif_id.name)
            if anio == apg_anio_fiscal and not r.pc_id.apg_afectada:
                self.pool.get('grp.pedido.compra').write(cr, uid, [r.pc_id.id], {'apg_afectada': True})
            # PCAR 11 08 2017 fin
            self.write(cr, uid, [r.id], {'state': 'afectado'}, context=context)

            partner_ids = [partner.id for partner in r.pc_id.message_follower_ids]

            msg = """El pedido de compra <a href="#action=mail.action_mail_redirect&amp;model=grp.pedido.compra&amp;res_id=%s">%s<a/>
            tiene la APG Nro. <a href="#action=mail.action_mail_redirect&amp;model=grp.compras.apg&amp;res_id=%s">%s<a/>
            afectada, por lo tanto Ud. puede enviar el pedido de compra a autorizar al ordenador """ % (
               r.pc_id.id, r.pc_id.name, r.id , r.name)
            context= dict(context)
            context.update({'mail_notify_noemail': True})
            self.pool.get('mail.thread').message_post(cr, uid, r.id, type="notification",
                                                      subtype='mt_comment', body=msg,
                                                      partner_ids=partner_ids, context=context)

        return True

    def act_apg_desafectado(self, cr, uid, ids, context=None):
        for r in self.browse(cr, uid, ids, context=context):
            # PCAR 11 08 2017 inicio Desmarcar flag apg_afectada en pc_id si cumple las condiciones
            pc_fecha_creacion = r.pc_id.date_start
            anio = datetime.strptime(pc_fecha_creacion, "%Y-%m-%d").date().year
            apg_anio_fiscal = int(r.fiscalyear_siif_id.name)
            apg_ids = self.search(cr, uid, [('pc_id', '=', r.pc_id.id), ('id', '!=', r.id)])
            if anio == apg_anio_fiscal and not apg_ids:
                self.pool.get('grp.pedido.compra').write(cr, uid, [r.pc_id.id], {'apg_afectada': False})
            # PCAR 11 08 2017 fin
            self.write(cr, uid, [r.id], {'state': 'desafectado'}, context=context)
        return True

    # def act_apg_rechazado(self, cr, uid, ids, context=None):
    #     for r in self.browse(cr, uid, ids, context=context):
    #         self.write(cr, uid, [r.id], {'state': 'rechazado'}, context=context)
    #     return True

    # # transiciones: se ejecutan las funciones previo a completar la señal
    # def trans_apg_inicio_nuevo(self, cr, uid, ids, context=None):
    #     return True

    # #TODO, esto va en el pasaje de borrador a financiero
    # def trans_apg_nuevo_en_aprobacion(self, cr, uid, ids, context=None):
    #     for rec in self.browse(cr, uid, ids, context):
    #         if rec.monto_divisa == 0:
    #             raise osv.except_osv('Error!', u'El monto a autorizar debe ser mayor a 0')
    #     return True
    #
    # #TODO: ver este control, ODG no va mas?
    # def trans_apg_en_aprobacion_aprobado(self, cr, uid, ids, context=None):
    #     self_obj = self.pool.get('grp.compras.apg').browse(cr, uid, ids[0], context=context)
    #     # Comprobar el odg obligatorio solo para el cambio de estado cambio 16/12
    #     if not self_obj.odg:
    #         raise osv.except_osv(('Error!!'), ('No hay un ODG seleccionado. Por favor, elija uno.'))
    #     dt = datetime.datetime.today()
    #     anio = dt.year
    #     monto_compras_id = self.pool.get('grp.monto.aprobacion').search(cr, uid, [('anio_vigencia', '=', anio)])
    #     monto_compras_obj = self.pool.get('grp.monto.aprobacion').browse(cr, uid, monto_compras_id, context=context)
    #     monto_hasta_p = 0
    #     monto_desde_p = 0
    #     monto_hasta_s = 0
    #     monto_desde_s = 0
    #     if monto_compras_obj:
    #         for line in monto_compras_obj[0].linea_ids:
    #             if line.tipo_trans == 'apg' and line.rol_id == 'odg_p':
    #                 monto_hasta_p = line.hasta
    #                 monto_desde_p = line.desde
    #             elif line.tipo_trans == 'apg' and line.rol_id == 'odg_s':
    #                 monto_hasta_s = line.hasta
    #                 monto_desde_s = line.desde
    #     else:
    #         raise osv.except_osv(('Error!!'), (u'No encontrado monto de aprobación para compra.'))
    #     total = self_obj.total_estimado
    #     if total >= monto_desde_p and total <= monto_hasta_p:
    #         if self.pool.get('res.users').has_group(cr, self_obj.odg.id,
    #                                                 'grp_seguridad.grp_compras_apg_Ordenador_del_gasto_primario'):
    #             return True
    #         else:
    #             raise osv.except_osv(('Error!!'), ('El ODG seleccionado no es un ODG primario.'))
    #     elif total >= monto_desde_s and total <= monto_hasta_s:
    #         if self.pool.get('res.users').has_group(cr, self_obj.odg.id,
    #                                                 'grp_seguridad.grp_compras_apg_Ordenador_del_gasto_secundario'):
    #             return True
    #         else:
    #             raise osv.except_osv(('Error!!'), ('El ODG seleccionado no es un ODG secundario.'))
    #
    # # 003-Fin
    # def trans_apg_en_aprobacion_rechazado(self, cr, uid, ids, context=None):
    #     return True
    #
    # def trans_apg_en_aprobacion_nuevo(self, cr, uid, ids, context=None):
    #     return True
    #
    # def trans_apg_en_aprobacion_en_autorizacion_ODG(self, cr, uid, ids, context=None):
    #     return True
    #
    # #TODO: ver este control, ODG no va mas?
    # def trans_apg_en_autorizacion_ODG_autorizado_ODG(self, cr, uid, ids, context=None):
    #     # chequeamos que el odg este autorizado para autorizar
    #     pool_aprobacion = self.pool.get('grp.monto.aprobacion')
    #     pool_subaprob = self.pool.get('grp.linea.monto.aprob')
    #     usuario = self.pool.get('res.users').browse(cr, uid, uid, context)
    #     apg = self.browse(cr, uid, ids, context=context)[0]
    #
    #     search_monto = pool_aprobacion.search(cr, 1, [('anio_vigencia', '=', apg.fecha.split('-')[0]),
    #                                                   ('activo_aprob', '=', True)], context=context)
    #     if not len(search_monto):
    #         raise osv.except_osv('Error!',
    #                              u'No existe configuración activa para el periodo correspondiente. Debe crear una configuración para montos de aprobación para los ordenadores del gasto y activarla o contactar al administrador de sistema!')
    #     listaroles = ['odg_p'] if self.pool.get('res.users').has_group(cr, uid,
    #                                                                    'grp_seguridad.grp_compras_apg_Ordenador_del_gasto_primario') else []
    #     listaroles += ['odg_s'] if self.pool.get('res.users').has_group(cr, uid,
    #                                                                     'grp_seguridad.grp_compras_apg_Ordenador_del_gasto_secundario') else []
    #     if len(listaroles) != 1:
    #         raise osv.except_osv('Error!',
    #                              u'No se encuentra configurado correctamente al ordenador del gasto, contacte al administrador del sistema!')
    #     rol = listaroles[0]
    #     config = pool_aprobacion.browse(cr, 1, search_monto, context=context)[0]
    #     subaprobacion = pool_subaprob.search(cr, 1, [('monto_aprob_id', '=', config.id), ('rol_id', '=', rol),
    #                                                  ('tipo_trans', '=', 'apg')], context=context)
    #     subaprob = pool_subaprob.browse(cr, 1, subaprobacion, context=context)[0]
    #     if apg.total_estimado >= subaprob.desde and apg.total_estimado <= subaprob.hasta:
    #         return True
    #     raise osv.except_osv('Error!', u'No puede autorizar el gasto, el monto se encuentra fuera del rango!')
    #
    # def trans_apg_en_autorizacion_ODG_rechazado(self, cr, uid, ids, context=None):
    #     return True
    #
    # def trans_apg_autorizado_ODG_afectado(self, cr, uid, ids, context=None):
    #     return True
    #
    # def trans_apg_afectado_desafectado(self, cr, uid, ids, context=None):
    #     return True


grp_compras_apg()


# ================================================================
#       Líneas de resumen de pedido de autorización para gastar
# ================================================================
class grp_compras_apg_lineas_resumen(osv.osv):
    _name = 'grp.compras.apg.lineas.resumen'
    _description = u'Líneas de resumen del pedido de compra copiadas para autorizar'

    def _get_monto_divisa(self, cr, uid, ids, fieldname, args, context=None):
        res = {}
        tax_obj = self.pool.get('account.tax')
        for line in self.browse(cr, uid, ids, context=context):
            if line.iva:
                taxes = tax_obj.compute_all(cr, uid, line.iva, line.precio_estimado, line.cantidad_a_comprar,
                                            product=line.product_id)
                res[line.id] = taxes['total_included']
            else:
                total = line.cantidad_a_comprar * line.precio_estimado
                res[line.id] = total
        return res

    def _get_importe_base(self, cr, uid, ids, name, arg, context=None):
        res = {}
        currency_obj = self.pool.get('res.currency')
        for line in self.browse(cr, uid, ids, context=context):
            moneda = line.apg_id.moneda.id
            moneda_base = line.apg_id.company_id.currency_id.id
            if moneda != moneda_base:
                # cambio para que funcione en version 8
                context = dict(context)
                context.update({'date': line.apg_id.fecha_tipo_cambio, 'pricelist_type': 'presupuesto'})
                res[line.id] = currency_obj.compute(cr, uid, moneda, moneda_base, line.subtotal_divisa, context=context)
            else:
                res[line.id] = line.subtotal_divisa
        return res

    _columns = {
        'apg_id': fields.many2one('grp.compras.apg', u'Autorización para gastar', ondelete='cascade'),
        'sice_num_ifaz': fields.char(u'Nro. de Ítem'),  # TODO carlos lamas
        'sice_cod_unidad': fields.char('CodUnidad'),  # TODO carlos lamas
        'sice_cod_articulo': fields.related('product_tmpl_id', 'grp_sice_cod', type='integer', string=u"Código SICE"),
        'objeto_del_gasto': fields.related('product_tmpl_id', 'grp_objeto_del_gasto', type='integer',
                                           string='Objeto del Gasto', store=False, readonly=True),
        # campos idem a resumen de PC
        # MVARELA 22_05 se saca el required
        'product_id': fields.many2one('product.product', u'Producto', ondelete='restrict', readonly=True),
        # 'product_id' : fields.many2one ( 'product.product', u'Producto', ondelete = 'restrict', readonly = True ),
        # MVARELA 22_05 se saca el readonly
        'product_tmpl_id': fields.many2one('product.template', u'Producto', required=True, ondelete='restrict',
                                           readonly=True, select=True),
        # 'product_tmpl_id' : fields.many2one('product.template', u'Producto', required=True, ondelete='restrict', select=True),
        'uom_id': fields.related('product_id', 'uom_id', type='many2one', relation='product.uom', string='UdM',
                                 store=False, readonly=True),
        'llave_presupuestal': fields.char('Llave Presupuestal'),  # TODO related
        'cantidad_a_comprar': fields.float('Cantidad a comprar', digits_compute=dp.get_precision('Cantidad'),
                                           required=True),
        'precio_estimado': fields.float('Precio Estimado', digits_compute=dp.get_precision('Cantidad'), required=True),
        # TODO function
        'subtotal': fields.function(_get_importe_base, type='float', digits_compute=dp.get_precision('Cantidad'),
                                    string='Total estimado pesos'),
        'subtotal_divisa': fields.function(_get_monto_divisa, type='float', digits_compute=dp.get_precision('Cantidad'),
                                           string='Total estimado divisa', store=True),
        'iva': fields.many2many('account.tax', 'apg_lineas_resumen_tax', 'linea_resumen_apg_id', 'tax_id', 'IVA'),
    }


grp_compras_apg_lineas_resumen()
