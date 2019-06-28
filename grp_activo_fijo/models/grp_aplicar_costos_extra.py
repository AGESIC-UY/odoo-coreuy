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
from lxml import etree
from openerp import exceptions, models, fields
from openerp import tools
from openerp.tools.translate import _
import time
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from openerp import models, api


#003-Inicio
# declaracion de la clase para la nueva pantalla de Aplicar Costos Extras
class GrpAplicarCostosExtras(models.Model):
    _name = 'grp.aplicar.costos.extra'

    @api.depends('account_asset_ids')
    def _get_advertencia_nc(self):
        res = {}
        for rec in self:
            hay_en_ejecucion = False
            for line in rec.account_asset_ids:
                if line.asignacion_ids:
                    for ass in line.asignacion_ids:
                        if ass.invoice_id.doc_type in ['in_refund', 'out_refund'] and line.asset_id.state in ['open']:
                            hay_en_ejecucion = True
            rec.advertencia_nc = hay_en_ejecucion

    @api.depends('account_invoice_ids')
    def _get_advertencia_nc_cancel(self):
        res = {}
        pool_invoice = self.env['account.invoice']
        for rec in self:
            cancela_total = False
            for il in rec.account_invoice_ids:
                if il.invoice_id.doc_type in ['in_refund', 'out_refund']:
                    inv_num = il.invoice_id.supplier_invoice_number
                    inv_ids = pool_invoice.search([('supplier_invoice_number', '=', inv_num),
                                                  ('doc_type', 'not in', ['in_refund', 'out_refund'])])
                    if len(inv_ids) > 0:
                        inv_ids = inv_ids[0]
                    inv_obj = inv_ids
                    if inv_obj.amount_total == il.invoice_id.amount_total:
                        cancela_total = True
            rec.advertencia_nc_cancel = cancela_total
        return res

    @api.onchange('proveedor_id')
    def onchange_proveedor_id(self):
        res = {}
        if self.proveedor_id:
            domain = str([('partner_id', '=', self.proveedor_id.id)])
            res.update({'domain': {'factura_id': domain}})
        else:
            res.update({'domain': {'factura_id': False}})
        return res

    # definicion de campos
    proveedor_id = fields.Many2one(
        comodel_name='res.partner',
        string=u"Proveedor"
    )
    factura_id = fields.Many2one(
        comodel_name='account.invoice',
        string=u"Nro. de Factura"
    )
    producto_id = fields.Many2one(
        comodel_name='product.product',
        string=u"Producto"
    )
    account_invoice_ids = fields.One2many(
        comodel_name='account.invoice.line',
        inverse_name='costos_extra_id',
        string=u'Lineas de Factura'
    )
    account_asset_ids = fields.One2many(
        comodel_name='grp.costos.extra.account.asset',
        inverse_name='costos_extra_id',
        string=u"Lineas de Activo"
    )

    advertencia_nc = fields.Boolean(
        string=u"Advertencia NC",
        compute="_get_advertencia_nc"
    )
    advertencia_nc_cancel = fields.Boolean(
        string=u"Advertencia NC Cancelación",
        compute="_get_advertencia_nc_cancel"
    )
    confirmado = fields.Boolean(
        string=u"Confirmado",
        default=False
    )
    cargo_montos = fields.Boolean(
        string=u"Cargo montos",
        default=False
    )
    estado = fields.Selection([('draft', u'Borrador'), ('done', u'Confirmado')], u'Estado', default='draft')

    @api.multi
    def cargar_asignaciones(self):
        for rec in self:
            lista = []
            for line in rec.account_invoice_ids:
                if line.seleccionar:
                    lista.append(line.id)
            values = {
                'asignacion_ids': [(6, 0, lista)]
            }
            for a in rec.account_asset_ids:
                self.env['grp.costos.extra.account.asset'].sudo().browse([a.id]).write(values)
            # self.browse([rec.id]).write(values)

    # definicion de metodos de botones
    @api.multi
    def action_actualizar(self):
        #Cargar datos en la grilla de lineas de factura
        # busqueda por las facturas que tienen cuenta contable de activo
        types = self.env['account.account.type'].search([('code', '=', 'asset')])
        cat_obras = self.env['account.asset.category'].search([('tipo', 'in', ['obc'])])
        account_objs = self.env['account.account'].search([('user_type', 'in', types.ids)])
        account_asset_obras = [cat.account_asset_id.id for cat in cat_obras]
        account_objs = [ac for ac in account_objs if ac.id not in account_asset_obras]
        for rec in self:
            self.sudo().browse([rec.id]).write({'account_invoice_ids': [(5,)]})
            pool_il = self.env['account.invoice.line']
            pool_ai = self.env['account.invoice']
            line_factura_ids = []
            if rec.factura_id:
                line_factura_ids = pool_il.sudo().search([('invoice_id', '=', rec.factura_id.id),
                                                   ('ass_processed', '=', False),
                                                   ('asset_category_id', '=', False),
                                                   ('account_id', 'in', [i.id for i in account_objs]),
                                                   ('product_es_activo_fijo', '=', False)])
                line_factura_ids = [lf.id for lf in line_factura_ids]
            line_prov_ids = []
            lista_lineas = []
            factura_ids = []
            if rec.proveedor_id:
                line_prov_ids = pool_ai.sudo().search([('partner_id', '=', rec.proveedor_id.id), ('state', 'in', ['open'])])
                line_prov_ids = [ai.id for ai in line_prov_ids]
                for id in line_prov_ids:
                    factura_ids = pool_il.sudo().search([('invoice_id', '=', id),
                                                  ('ass_processed', '=', False),
                                                  ('asset_category_id', '=', False),
                                                  ('account_id', 'in', [i.id for i in account_objs]),
                                                  ('product_es_activo_fijo', '=', False)])
                    factura_ids = [f.id for f in factura_ids]
                    lista_lineas += factura_ids
            if rec.proveedor_id and rec.factura_id:
                if line_factura_ids and lista_lineas:
                    lines = list(set(line_factura_ids) & set(lista_lineas))  # hace la interseccion de las listas
                else:
                    lines = []
            elif rec.proveedor_id:
                lines = lista_lineas
            elif rec.factura_id:
                lines = line_factura_ids
            else:
                lines = []
            _logger.info("Lines: %s", lines)
            self.sudo().browse([rec.id]).write({'account_invoice_ids': [(6, 0, lines)]})
        return True

    # @api.multi
    # def action_asignar_activos(self):
    #     ctx = self._context and self._context.copy() or {}
    #     list_lineas = []
    #     seleccionados = []
    #     for rec in self:
    #         query = """select distinct af.id as id from account_asset_asset af, account_asset_depreciation_line adl
    #            where adl.asset_id = af.id and not adl.move_check and state not in ('close')"""
    #         if rec.producto_id:
    #             query += """ and af.product_id = %s"""
    #             self._cr.execute(query, [rec.producto_id.id])
    #         else:
    #             self._cr.execute(query)
    #         lista = [t[0] for t in self._cr.fetchall()]
    #         for id in lista:
    #             asset_obj = self.env['account.asset.asset'].browse(id)
    #             values = {
    #                 'costos_extra_id': rec.id,
    #                 'account_asset_id': asset_obj.id,
    #                 'name': asset_obj.name,
    #                 'note': asset_obj.note,
    #                 'asignacion_ids': False,
    #                 'department_id': asset_obj.department_id.id,
    #                 'category_id': asset_obj.category_id.id,
    #                 'resultado': 0,
    #             }
    #             list_lineas.append((0, 0, values))
    #         for line in rec.account_invoice_ids:
    #             if line.seleccionar:
    #                 seleccionados.append(line.id)
    #         ctx['default_costos_extra_id'] = rec.id
    #     ctx['default_account_asset_ids'] = list_lineas
    #     ctx['seleccionados'] = seleccionados
    #
    #     return {
    #         'type': 'ir.actions.act_window',
    #         'view_type': 'form',
    #         'view_mode': 'form',
    #         'res_model': 'grp.asignacion.activos',
    #         'target': 'new',
    #         'context': ctx,
    #     }

    @api.multi
    def action_vista_previa(self):
        for rec in self:
            rec.cargar_asignaciones()
            inv_line_qty = []
            for inv_line in rec.account_invoice_ids:
                count = 0
                for ass_line in rec.account_asset_ids:
                    if inv_line.id in [line.id for line in ass_line.asignacion_ids]:
                        count += 1
                if count > 0:
                    resultado = inv_line.importe_imp_incl / count
                    resultado = round(resultado, 2)  # Redondeo a 2 cifras para que el resto se asigne a la ultima linea
                else:
                    resultado = 0
                inv_line_qty.append((inv_line.id, resultado))

            ultimo = False
            total_resultado = 0
            total_importe = 0
            ultimo_resultado = 0
            il_list = []
            for ass_line in rec.account_asset_ids:
                resultado = 0
                invoice_list = []
                for asignacion in ass_line.asignacion_ids:
                    if asignacion.id not in il_list:
                        total_importe += asignacion.importe_imp_incl
                        il_list.append(asignacion.id)
                    invoice_list.append(asignacion.invoice_id.id)
                    for elem in inv_line_qty:
                        if elem[0] == asignacion.id:
                            resultado += elem[1]
                    ultimo = ass_line.id
                    ultimo_resultado = resultado
                invoice_list = list(set(invoice_list))  # elimina duplicados
                pool_af = self.env['grp.costos.extra.account.asset']
                pool_af.browse([ass_line.id]).write({'resultado': resultado})
                total_resultado += resultado

            # chequear que el total de resultados menos el total de importes da 0.
            # si no es el caso, agregar el saldo restante a la ultima linea de activo.
            if abs(total_resultado - total_importe) != 0:
                resto = abs(total_resultado - total_importe)
                if total_resultado > total_importe:
                    ultimo_resultado -= resto
                else:
                    ultimo_resultado += resto
                pool_af.browse([ultimo]).write({'resultado': ultimo_resultado})
            rec.write({'cargo_montos': True})

        return True

    @api.multi
    def action_confirmar(self):
        # self_obj = self.browse(cr, uid, ids[0])
        for rec in self:
            pool_asset = self.env['account.asset.asset']
            currency_obj = self.env['res.currency']
            invoice_line_obj = self.env['account.invoice.line']
            for ass_line in rec.account_asset_ids:
                invoice_list = []
                fecha_factura = False
                moneda_factura = False
                for asignacion in ass_line.asignacion_ids:
                    invoice_list.append(asignacion.invoice_id.id)
                    fecha_factura = asignacion.invoice_id.fecha_contabilizado
                    moneda_factura = asignacion.invoice_id.currency_id.name in ['USD']
                    invoice_line_obj.sudo().browse([asignacion.id]).write({'ass_processed': True})
                invoice_list = list(set(invoice_list))  # elimina duplicados
                # conversion del monto resultado a USD
                resultado = ass_line.resultado
                if moneda_factura:
                    ctx = self._context.copy()
                    ctx.update({'date': fecha_factura})
                    moneda_usd = currency_obj.search([('name', 'in', ['USD'])])
                    moneda_uyu = currency_obj.search([('name', 'in', ['UYU'])])
                    resultado = currency_obj.compute(moneda_usd.id, moneda_uyu.id, ass_line.resultado)
                _logger.info("Activo: %s", ass_line.account_asset_id)
                _logger.info("Lista facturas: %s", invoice_list)

                # cargar en la relacion many2many la asociacion de activo a account.invoice
                for inv_id in invoice_list:
                    self._cr.execute("""
                    INSERT INTO ass_asset_invoice_rel (asset_id, invoice_id)
                    VALUES (%s, %s)
                    """, [ass_line.account_asset_id.id, inv_id])
                # Fin

                pool_asset.browse([ass_line.account_asset_id.id]).write({
                                  'purchase_value': ass_line.account_asset_id.purchase_value + resultado})
                ctx = self._context.copy()
                ctx.update({'factura_activo': True,
                                'resultado': resultado,
                                'fecha_contabilizado': fecha_factura,
                                'es_usd': moneda_factura})
                if ass_line.asignacion_ids:
                    pool_asset.browse([ass_line.account_asset_id.id]).with_context(ctx).compute_depreciation_board()
                    # ass_line.account_asset_id.compute_depreciation_board(cr, uid, ids, context=context)

                self.browse([rec.id]).write({'confirmado': True, 'estado': 'done'})

            lista_unlink = []
            for line in rec.account_invoice_ids:
                if line.seleccionar:
                    line.sudo().write({'ass_processed': True})
                else:
                    lista_unlink.append((3, line.id))
            if lista_unlink:
                self.browse([rec.id]).write({'account_invoice_ids': lista_unlink})

        return True


class GrpCostosExtraAccountAsset(models.Model):
    _name = 'grp.costos.extra.account.asset'

    # definicion de campos
    costos_extra_id = fields.Many2one(
        comodel_name='grp.aplicar.costos.extra',
        string=u'Costo extra'
    )
    account_asset_id = fields.Many2one(
        comodel_name='account.asset.asset',
        string=u'Activo Fijo'
    )
    name = fields.Char(
        string='Name',
        size=50,
        select=1,
        related='account_asset_id.name'
    )
    note = fields.Text(
        string='Note',
        related='account_asset_id.note'
    )
    asignacion_ids = fields.Many2many(
        comodel_name='account.invoice.line',
        relation='costo_extra_activo_factura_rel',
        column1='costo_extra_asset_id',
        column2='invoice_line_id',
        string=u'Asignación'
    )
    resultado = fields.Float(
        string=u'Resultado'
    )
    department_id = fields.Many2one(
        comodel_name='hr.department',
        string=u'Ubicación',
        select="1",
        related='account_asset_id.department_id'
    )
    category_id = fields.Many2one(
        comodel_name='account.asset.category',
        string=u'Categoria de Activo',
        related='account_asset_id.category_id'
    )
    state = fields.Selection(
        selection=[('draft', 'Draft'), ('open', 'Running'), ('close', 'Close')], string=u'Status',
        help="When an asset is created, the status is 'Draft'.\n" \
        "If the asset is confirmed, the status goes in 'Running' and the depreciation "
             "lines can be posted in the accounting.\n" \
        "You can manually close an asset when the depreciation is over. If the last line"
             " of depreciation is posted, the asset automatically goes in that status.",
        related='account_asset_id.state'
    )
    # fin definicion de campos


class GrpAccountInvoiceLineInherited(models.Model):
    _inherit = 'account.invoice.line'

    @api.depends('costos_extra_id')
    def _get_id_linea(self):
        _logger.info("id de linea funcional")
        res = {}
        for rec in self:
            rec.id_line = rec.id

    # definicion de campos
    id_line = fields.Integer(
        compute='_get_id_linea',
        string=u'Id de línea',
        store=True
    )
    costos_extra_id = fields.Many2one(
        comodel_name='grp.aplicar.costos.extra',
        string=u"Costo extra"
    )
    ass_processed = fields.Boolean(
        string=u"Asignación procesada",
        default=False
    )
    # fin definicion campos

class GrpAccountAssetCostosExtra(models.Model):
    _inherit = 'account.asset.asset'

    product_id = fields.Many2one(
        comodel_name='product.product',
        string=u'Producto'
    )

#PCAR 29 03 2017 Inicio
class GrpAccountInvoiceInh(models.Model):
    _inherit = 'account.invoice'

    asset_id = fields.Many2one(
        comodel_name='account.asset.asset',
        string=u'Activo fijo'
    )
    fecha_contabilizado = fields.Date(
        string=u'Fecha contabilizado'
    )

    @api.multi
    def invoice_validate(self):
        _logger.info("Entra a invoice_validate de grp_atributos_activos")
        res = super(GrpAccountInvoiceInh, self).invoice_validate()
        for rec in self:
            self.browse([rec.id]).write({'fecha_contabilizado': time.strftime('%Y-%m-%d')})
        return True

    @api.multi
    def invoice_cancel(self):
        _logger.info("Entra a invoice_cancel de grp_atributos_activos")
        for self_obj in self:
            if self_obj.asset_id:
                if self_obj.asset_id.state not in ['cancel']:
                    raise exceptions.ValidationError(u'Debe dar de baja el activo antes de cancelar la factura.')
            for line in self_obj.invoice_line:
                line.write({'ass_processed': False})
        return super(GrpAccountInvoiceInh, self).invoice_cancel()

    @api.multi
    def button_cancelar_pago(self):
        for self_obj in self:
            for line in self_obj.invoice_line:
                line.write({'ass_processed': False})
        return super(GrpAccountInvoiceInh, self).button_cancelar_pago()

# Mej-AF-2 Vinculo entre Productos y AF
class GrpComprasProductAtributosActivosInh(models.Model):
    _inherit = 'product.product'

    account_asset_ids = fields.One2many('account.asset.asset','product_id', string=u'Activos')

    @api.multi
    def action_ver_activos(self):
        # self_obj = self.browse(cr, uid, ids[0])
        for rec in self:
            ctx = self._context.copy()
            return {
                'name': 'Assets',
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'account.asset.asset',
                'view_id': False,
                'domain': [('id', 'in', [line.id for line in rec.account_asset_ids])],
                'context': ctx,
            }

#PCAR 29 03 2017 Fin
