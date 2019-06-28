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
from openerp import SUPERUSER_ID
import time
from collections import defaultdict
from openerp.tools.translate import _


# ================================================================
## COTIZACIONES
# ================================================================

class grp_cotizaciones(osv.osv):
    _inherit = 'grp.cotizaciones'

    def button_Crear_OC(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        context=dict(context)
        order_pool = self.pool.get('purchase.order')
        product_product = self.pool.get('product.product')
        order_ids = []
        rate_date = time.strftime('%Y-%m-%d')
        for cotizacion in self.browse(cr, uid, ids, context=context):
            pc_apg_id = False
            if cotizacion.pedido_compra_id.id:
                if cotizacion.pedido_compra_id.apg_ids:
                    for apg in cotizacion.pedido_compra_id.apg_ids:
                        if apg.state != 'anulada':
                            pc_apg_id = apg.id
                            break
                else:
                    raise osv.except_osv('Error!', u'No hay APG asociada al pedido de compra.')
            ordenes_a_crear = defaultdict(lambda:[])
            for lineas in cotizacion.sice_page_aceptadas:
                key = str(lineas.proveedor_cot_id.id) + str(lineas.currency.id)
                ordenes_a_crear[key].append(lineas)

            for k,v in ordenes_a_crear.items():
                newlines = []
                llavep_data = []
                cotizacion_values_lines = []
                if v[0].currency.id:
                    context.update({'date': rate_date})
                    currency = self.pool.get('res.currency').browse(cr, uid, v[0].currency.id, context=context)
                    rate = currency.rate_presupuesto
                else:
                    raise osv.except_osv ( 'Error!', u'Debe definir la moneda!' )
                #Default location
                loc_id = self._get_location(cr, uid, cotizacion, context=context),
                if loc_id:
                    picking_aux = self._get_picking(cr, uid, loc_id)
                else:
                    picking_aux = False
                values = {
                    'doc_origen' : cotizacion.id,
                    'origin' : cotizacion.name,
                    'notes' : cotizacion.observaciones,
                    'descripcion' : cotizacion.sice_descripcion,
                    'partner_id' : v[0].proveedor_cot_id.id,
                    'pedido_compra_id' : cotizacion.pedido_compra_id.id or False,
                    'pc_apg_id' : pc_apg_id or False,
                    'currency_oc' : v[0].currency.id,
                    'cod_moneda' : v[0].cod_moneda.id,
                    'tipo_de_cambio': rate or False,
                    'fecha_tipo_cambio_oc': rate_date,
                    'order_line' : newlines,
                    'page_apg_oc': False,
                    'location_id' : loc_id,
                    'pricelist_id' : self.pool.get('res.partner').browse(cr,SUPERUSER_ID,v[0].proveedor_cot_id.id).property_product_pricelist_purchase.id,
                    'picking_type_id': picking_aux,
                }

                for linea_apg in cotizacion.page_apg:
                    cotizacion_values_lines.append((0,0, {
                        'nro_apg': linea_apg.id,
                        'descripcion_apg': linea_apg.descripcion,
                        'monto_apg': linea_apg.monto,
                        'currency': linea_apg.moneda.id,
                        'fecha_apg': linea_apg.fecha,
                        'nro_afectacion_apg': linea_apg.nro_afectacion_siif,
                    }))
                if cotizacion_values_lines:
                    values.update({'page_apg_oc': cotizacion_values_lines})
                # inicializando diccionario lineas agrupadas

                lineas_crear = defaultdict(lambda:[])
                for lines in v:
                    if not lines.product_id:
                        raise osv.except_osv('Error!', u'No hay producto definido en alguna línea de la adjudicación!' )
                    key = str(lines.product_id.id)
                    lineas_crear[key].append(lines)
                data_prod_group = defaultdict(lambda:[])
                for k,v in lineas_crear.items():
                    first_taxes = []
                    rest_taxes = []
                    sum_ttal = 0.0
                    sum_cantidad = 0.0
                    i = 0
                    for elem in v:
                        sum_ttal += elem.precio * elem.cantidad  #elem.subtotal
                        sum_cantidad += elem.cantidad
                        if elem.iva:
                            ivas = [x.id for x in elem.iva]
                            if i==0:
                                first_taxes.append(ivas)
                            else:
                                rest_taxes.append(ivas)
                        i+=1
                    if first_taxes:
                        # if len(first_taxes[0]) != len(rest_taxes[0]):
                        #     raise osv.except_osv('Error!', u'Los impuestos de los productos deben ser correspondientes!' )
                        for tax in first_taxes[0]:
                            for rtax in rest_taxes:
                                if tax not in rtax or len(first_taxes[0]) != len(rtax):
                                    raise osv.except_osv('Error!', u'Los impuestos de los productos deben ser correspondientes!' )

                    data_prod_group[k]={'precio': sum_ttal / sum_cantidad, 'cantidad':sum_cantidad }


                for k,v in lineas_crear.items():
                    dummy, prod_name = product_product.name_get(cr, uid, v[0].product_id.id, context=context)[0]
                    newlines.append((0,0,{
                            'product_id' : v[0].product_id.id,
                            'product_uom' : v[0].uom_id.id,
                            'name' : prod_name or v[0].product_id.product_tmpl_id.description or '', # incidencia
                            'date_planned' : cotizacion.fecha_respuesta,
                            'product_qty' : data_prod_group[k]['cantidad'], #  v[0].cantidad,
                            'price_unit' : data_prod_group[k]['precio'], #lines.precio,
                            'taxes_id':  [(6, 0, [x.id for x in v[0].iva])],
                            # 'taxes_id' :  [(6, 0, [x.id for x in lines.tax_id])],
                            #MVARELA 24_03 - Campos intefaz SICE
                            'id_variacion': v[0].id_variacion,
                            'id_item': v[0].id_item,
                            'cod_moneda': v[0].cod_moneda.id,
                            'desc_variacion': v[0].desc_variacion,
                            'cotizaciones_linea_id': v[0].id,  # TODO: SPRING 12 GAP 67 K
                    }))

                #ACTUALIZAR FECHA CONTEXTO
                fiscalyear_obj = self.pool.get('account.fiscalyear')
                uid_company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
                fecha_hoy = cotizacion.fecha_respuesta
                if fecha_hoy:
                    fiscal_year_id = fiscalyear_obj.search(cr, uid, [('date_start','<=',fecha_hoy),('date_stop','>=',fecha_hoy),('company_id','=',uid_company_id)], context=context)
                    fiscal_year_id = fiscal_year_id and fiscal_year_id[0] or False
                    context.update({'fiscalyear_id': fiscal_year_id})

                    values.update({'fiscalyear_siif_id':fiscal_year_id})
                values['operating_unit_id'] = cotizacion.operating_unit_id.id
                id_order = order_pool.create(cr, uid, values, context=context)
                order_ids.append(id_order)
        if order_ids:
            data_pool = self.pool.get('ir.model.data')
            action_model,action_id = data_pool.get_object_reference(cr, uid, 'grp_compras_estatales', 'purchase_form2_action')
            if action_model:
                action_pool = self.pool.get(action_model)
                action = action_pool.read(cr, uid, action_id, context=context)
                action['domain'] = "[('id','in', ["+','.join(map(str,order_ids))+"])]"
            return action

        return True

    # Crear OC a partir de la ampliacion + grp.cotizaciones.lineas.ampliadas
    def button_Crear_OC_adjudicacion_ampliada(self, cr, uid, ids, pedido_compra_id, context=None):
        order_pool = self.pool.get('purchase.order')
        product_product = self.pool.get('product.product')
        order_ids = []

        pc_apg_id = False
        if pedido_compra_id.apg_ids:
            for apg in pedido_compra_id.apg_ids:
                if apg.state != 'anulada':
                    pc_apg_id = apg.id
                    break
        else:
            raise osv.except_osv('Error!', u'No hay APG asociada al pedido de compra.')

        cotizacion = self.browse(cr, uid, ids, context=context)[0]

        ordenes_a_crear = defaultdict(lambda: [])
        for line_ampliacion in cotizacion.lines_ampliacion_ids:
            if line_ampliacion.pc_ampliado_id.id == pedido_compra_id.id:
                key = str(line_ampliacion.proveedor_cot_id.id) + str(line_ampliacion.currency.id)
                ordenes_a_crear[key].append(line_ampliacion)

                # ordenes_a_crear[lineas.proveedor_cot_id.id].append(lineas)
        for k, v in ordenes_a_crear.items():
            newlines = []
            llavep_data = []
            cotizacion_values_lines = []
            apg_values_lines = []
            if v[0].currency.id:
                ctx = context.copy()
                ctx.update({'date': time.strftime('%Y-%m-%d')})
                currency = self.pool.get('res.currency').browse(cr, uid, v[0].currency.id, context=ctx)
                rate = currency.rate
            else:
                raise osv.except_osv('Error!', u'Debe definir la moneda!')
            values = {
                'descripcion': v[0].sice_descripcion or False,  # campo nuevo agregado en lineas sice ampliacion
                'partner_id': v[0].proveedor_cot_id.id,
                'pedido_compra_id': v[0].pc_ampliado_id.id or False,
                'pc_apg_id': pc_apg_id or False,
                'currency_oc': v[0].currency.id,
                'cod_moneda': v[0].cod_moneda.id,
                'tipo_de_cambio': rate or False,
                'order_line': newlines,
                'page_apg_oc': False,
                'location_id': self._get_location(cr, uid, cotizacion, context=context),
                'pricelist_id': self.pool.get('res.partner').browse(cr, SUPERUSER_ID, v[
                    0].proveedor_cot_id.id).property_product_pricelist_purchase.id,
            }

            # Para la APG
            if pedido_compra_id.apg_ids:
                for apg in pedido_compra_id.apg_ids:
                    if apg.id == pc_apg_id:
                        apg_values_lines.append((0, 0, {
                            'nro_apg': apg.id,
                            'descripcion_apg': apg.descripcion,
                            'monto_apg': apg.monto_divisa,  # puede ser monto pesos  monto
                            'currency': apg.moneda.id,
                            'fecha_apg': apg.fecha,
                            'nro_afectacion_apg': apg.nro_afectacion_siif
                        }))
                    # PARA LLAVE PRESUPUESTAL
                    if apg.llpapg_ids:
                        for llavep in apg.llpapg_ids:  # la seleccionada
                            llavep_data.append((0, 0, {
                                'programa': llavep.programa,
                                'sub_programa': llavep.sub_programa,
                                'odg': llavep.odg,
                                'auxiliar': llavep.auxiliar,
                                'disponible': llavep.disponible,
                                'proyecto': llavep.proyecto,
                                'fin': llavep.fin,
                                'mon': llavep.mon,
                                'tc': llavep.tc,
                                'importe': llavep.importe,
                                'programa_id': llavep.programa_id.id,
                                'odg_id': llavep.odg_id.id,
                                'auxiliar_id': llavep.auxiliar_id.id,
                                'proyecto_id': llavep.proyecto_id.id,
                                'fin_id': llavep.fin_id.id,
                                'mon_id': llavep.mon_id.id,
                                'tc_id': llavep.tc_id.id,
                            }))
                if llavep_data:
                    values.update({'llpapg_ids': llavep_data})

                if apg_values_lines:
                    values.update({'page_apg_oc': apg_values_lines})

            # inicializando diccionario lineas agrupadas
            lineas_crear = defaultdict(lambda: [])
            for lines in v:
                if not lines.product_id:
                    raise osv.except_osv('Error!', u'No hay producto definido en alguna línea de la adjudicación!')
                key = str(lines.product_id.id)
                lineas_crear[key].append(lines)
            data_prod_group = defaultdict(lambda: [])
            for k, v in lineas_crear.items():
                first_taxes = []
                rest_taxes = []
                sum_ttal = 0.0
                sum_cantidad = 0.0
                i = 0
                for elem in v:
                    sum_ttal += elem.precio * elem.cantidad  # elem.subtotal
                    sum_cantidad += elem.cantidad
                    if elem.iva:
                        ivas = [x.id for x in elem.iva]
                        if i == 0:
                            first_taxes.append(ivas)
                        else:
                            rest_taxes.append(ivas)
                    i += 1
                if first_taxes:
                    # if len(first_taxes[0]) != len(rest_taxes[0]):
                    #     raise osv.except_osv('Error!', u'Los impuestos de los productos deben ser correspondientes!' )
                    for tax in first_taxes[0]:
                        for rtax in rest_taxes:
                            if tax not in rtax or len(first_taxes[0]) != len(rtax):
                                raise osv.except_osv('Error!',
                                                     u'Los impuestos de los productos deben ser correspondientes!')

                data_prod_group[k] = {'precio': sum_ttal / sum_cantidad, 'cantidad': sum_cantidad}


            for k, v in lineas_crear.items():
                dummy, prod_name = product_product.name_get(cr, uid, v[0].product_id.id, context=context)[0]
                newlines.append((0, 0, {
                    'product_id': v[0].product_id.id,
                    'product_uom': v[0].uom_id.id,
                    'name': prod_name or v[0].product_id.product_tmpl_id.description or '',
                    'date_planned': cotizacion.fecha_respuesta,
                    'product_qty': data_prod_group[k]['cantidad'],
                    'price_unit': data_prod_group[k]['precio'],
                    'taxes_id': [(6, 0, [x.id for x in v[0].iva])],
                    'id_variacion': v[0].id_variacion,
                    'id_item': v[0].id_item,
                    'cod_moneda': v[0].cod_moneda.id,
                    'desc_variacion': v[0].desc_variacion,
                    'cotizaciones_linea_id': v[0].id,  # TODO: SPRING 12 GAP 67 K

                }))
            id_order = order_pool.create(cr, uid, values, context=context)
            order_ids.append(id_order)
        if order_ids:
            data_pool = self.pool.get('ir.model.data')
            action_model, action_id = data_pool.get_object_reference(cr, uid, 'grp_compras_estatales',
                                                                     'purchase_form2_action')
            if action_model:
                action_pool = self.pool.get(action_model)
                action = action_pool.read(cr, uid, action_id, context=context)
                action['domain'] = "[('id','in', [" + ','.join(map(str, order_ids)) + "])]"
            return action
        return True

    def act_cotizaciones_cancelado(self, cr, uid, ids, context=None):
        for rec in self.browse(cr, uid, ids, context=context):
            # dar error si alguno de los contratos asociados este en un estado diferente a cancelado
            for contrato in rec.contratos_ids:
                if contrato.state not in ['cancel']:
                    raise osv.except_osv('Error!', u'No puede cancelar la Adjudicación si tiene contratos'
                                                   u' asociados sin cancelar.')
            # dar error si alguna de las OC asociadas este en un estado diferente a cancelado
            for oc in rec.purchase_order_ids:
                if oc.state not in ['cancel']:
                    raise osv.except_osv('Error!', u'No puede cancelar la Adjudicación si tiene órdenes de compra '
                                                   u' asociadas sin cancelar.')
            # dar error si alguna de las PC asociadas este en un estado diferente a cancelado
            for pc in rec.pdc_ampliacion_ids:
                if pc.state not in ['cancelado', 'cancelado_sice']:
                    raise osv.except_osv('Error!', u'No puede cancelar la Adjudicación si tiene pedidos de compra '
                                                   u' ampliados sin cancelar.')
            for comp in rec.provider_compromise_ids:
                if comp.state not in ['anulado']:
                    raise osv.except_osv('Error!', u'No puede cancelar la Adjudicación si tiene compromisos'
                                                   u' de proveedor sin anular.')
            self.write(cr, uid, [rec.id], {'state': 'cancelado'}, context=context)
        return True

class grp_cotizaciones_compromiso_proveedor_llavep(osv.osv):
    _name = 'grp.cotizaciones.compromiso.proveedor.llavep'
    _description = 'Lineas de llave presupuestal para el compromiso por proveedor'

    def _check_linea_llavep_programa(self, cr, uid, ids):
        for llp in self.browse(cr, uid, ids):
            if llp.programa:
                if not llp.programa.isdigit():
                    return False
        return True

    def _check_linea_llavep_odg(self, cr, uid, ids):
        for llp in self.browse(cr, uid, ids):
            if llp.odg:
                if not llp.odg.isdigit():
                    return False
        return True

    def _check_linea_llavep_auxiliar(self, cr, uid, ids):
        for llp in self.browse(cr, uid, ids):
            if llp.auxiliar:
                if not llp.auxiliar.isdigit():
                    return False
        return True

    def _check_linea_llavep_disponible(self, cr, uid, ids):
        for llp in self.browse(cr, uid, ids):
            if llp.disponible:
                if not llp.disponible.isdigit():
                    return False
        return True

    def _check_linea_llavep_proyecto(self, cr, uid, ids):
        for llp in self.browse(cr, uid, ids):
            if llp.proyecto:
                if not llp.proyecto.isdigit():
                    return False
        return True

    def _check_linea_llavep_fin(self, cr, uid, ids):
        for llp in self.browse(cr, uid, ids):
            if llp.fin:
                if not llp.fin.isdigit():
                    return False
        return True

    def _check_linea_llavep_mon(self, cr, uid, ids):
        for llp in self.browse(cr, uid, ids):
            if llp.mon:
                if not llp.mon.isdigit():
                    return False
        return True

    def _check_linea_llavep_tc(self, cr, uid, ids):
        for llp in self.browse(cr, uid, ids):
            if llp.tc:
                if not llp.tc.isdigit():
                    return False
        return True

    _columns = {
        #many2one relacionados a los documentos correspondientes
        'compromiso_id': fields.many2one('grp.cotizaciones.compromiso.proveedor', u'Compromiso por proveedor', ondelete='cascade'),
        #Campos de la estructura
        'odg_id': fields.many2one('grp.estruc_pres.odg', 'ODG', required=True),
        'auxiliar_id': fields.many2one('grp.estruc_pres.aux', 'Auxiliar', required=True),
        'fin_id': fields.many2one('grp.estruc_pres.ff', 'Fin', required=True),
        'programa_id': fields.many2one('grp.estruc_pres.programa', 'Programa', required=True),
        'proyecto_id': fields.many2one('grp.estruc_pres.proyecto', 'Proyecto', required=True),
        'mon_id': fields.many2one('grp.estruc_pres.moneda', 'Mon', required=True),
        'tc_id': fields.many2one('grp.estruc_pres.tc', 'TC', required=True),
        # Campos related
        'odg': fields.related('odg_id', 'odg', type='char', string='ODG related', store=True, readonly=True),
        'auxiliar': fields.related('auxiliar_id', 'aux', type='char', string='Auxiliar related', store=True, readonly=True),
        'fin': fields.related('fin_id', 'ff', type='char', string='Fin related', store=True, readonly=True),
        'programa': fields.related('programa_id', 'programa', type='char', string='Programa related', store=True, readonly=True),
        'proyecto': fields.related('proyecto_id', 'proyecto', type='char', string='Proyecto related', store=True, readonly=True),
        'mon': fields.related('mon_id', 'moneda', type='char', string='Mon related', store=True, readonly=True),
        'tc': fields.related('tc_id', 'tc', type='char', string='TC related', store=True, readonly=True),
        #montos
        'disponible': fields.char('Disponible', size=3),  # de 8 a 3 #TODO: VER, CHAR Y DE 3?
        'importe': fields.integer('Importe'),

    }

    def _check_llavep_unica(self, cr, uid, ids, context=None):
        for line in self.browse(cr, uid, ids, context=context):
            lineas_duplicadas = self.search(cr, uid, [('compromiso_id', '=', line.compromiso_id.id),
                                                      ('fin_id', '=', line.fin_id.id),
                                                      ('mon_id', '=', line.mon_id.id),
                                                      ('odg_id', '=', line.odg_id.id),
                                                      ('programa_id', '=', line.programa_id.id),
                                                      ('proyecto_id', '=', line.proyecto_id.id),
                                                      ('tc_id', '=', line.tc_id.id),
                                                      ('id', 'not in', ids)
                                                      ], context=context)
            if lineas_duplicadas:
                raise osv.except_osv(
                    _(u'Línea duplicada'),
                    _(u'No se pueden ingresar 2 líneas iguales para el mismo registro.'))
        return True


    _constraints = [
        (_check_llavep_unica, u'Línea duplicada',
         ['auxiliar_id', 'compromiso_id', 'fin_id', 'mon_id', 'odg_id',
          'programa_id', 'proyecto_id', 'tc_id']),
        (_check_linea_llavep_programa, u'Campo no es numérico', ['programa']),
        (_check_linea_llavep_odg, u'Campo no es numérico', ['odg']),
        (_check_linea_llavep_auxiliar, u'Campo no es numérico', ['auxiliar']),
        (_check_linea_llavep_disponible, u'Campo no es numérico', ['disponible']),
        (_check_linea_llavep_proyecto, u'Campo no es numérico', ['proyecto']),
        (_check_linea_llavep_fin, u'Campo no es numérico', ['fin']),
        (_check_linea_llavep_mon, u'Campo no es numérico', ['mon']),
        (_check_linea_llavep_tc, u'Campo no es numérico', ['tc']),
    ]