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

import time
from openerp.osv import osv, fields
import openerp.addons.decimal_precision as dp
from openerp import SUPERUSER_ID
from openerp.tools.sql import drop_view_if_exists


# para el reporte de lineas de retenciones
class retention_lines_list_report(osv.Model):
    _name = "retention.lines.list.report"
    _description = "Listado de retenciones"
    _order = "id desc"
    _auto = False

    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if not ids:
            return []
        res = []
        reads = self.browse(cr, uid, ids, context=context)
        for record in reads:
            name = '%s - %s - %s' % (record.numero_factura, record.tipo_retencion, record.iva)
            res.append((record.id, name))
        return res

    _columns = {
        'id': fields.integer('Id', readonly=True),
        'id_objeto': fields.integer(u'ID Objeto', readonly=True, select=False),
        'invoice_id': fields.many2one('account.invoice', u'Factura', required=True, select=True, ondelete="cascade"),
        'nro_obligacion': fields.integer(u'Nº obligación', size=3),  # size=12),
        'numero_factura': fields.char(u'Número factura', size=364, readonly=True),
        'no_interno_factura': fields.char(u'Número', size=364, readonly=True),
        'currency_id': fields.many2one('res.currency', 'Moneda'),
        'proveedor': fields.char(u'Proveedor', size=128, required=True, select=True),
        'rut': fields.char(u'RUT', size=32, required=True, select=True),
        'iva': fields.char(u'IVA', size=32, required=True, select=True),
        'monto_retencion': fields.float(u'Monto retención', digits_compute=dp.get_precision('Account')),  # base linea
        'tipo_retencion': fields.char(u'Tipo de retención', size=10, required=True, select=True),
        'tipo': fields.char(u'Tipo', size=10, required=True, select=True),
        'state': fields.selection([
            ('draft', 'Draft'),
            ('proforma', 'Pro-forma'),
            ('proforma2', 'Pro-forma'),
            # ('confirmed',u'Confirmado/a'),
            ('sice', u'SICE'),
            ('cancel_sice', u'Anulado SICE'),
            # Nuevos estados para la OPI
            ('in_approved', u'En Aprobación'),
            ('approved', u'Aprobado'),
            ('in_auth', u'En Autorización'),  # in authorization
            ('authorized', u'Autorizado'),
            ('forced', u'Obligado'),
            # nuevos estados para obligado
            # Obligado – nuevo estado  utilizar forced
            ('intervened', u'Intervenida'),
            ('prioritized', u'Priorizada'),
            ('cancel_siif', u'Anulado SIIF'),
            # Anular Obligacion = a estado Anulado SIIF  ('cancel_forced',u'Anulado Obligación')
            # estandar
            ('open', 'Open'),
            ('paid', 'Paid'),
            ('cancel', 'Cancelled'),
        ], u'Estado', select=True, readonly=True),
        'importe_total': fields.float(u'Importe total', digits_compute=dp.get_precision('Account')),
        # importe total factura
        'importe_sin_iva': fields.float(u'Importe factura', digits_compute=dp.get_precision('Account')),
        # Importe factura sin iva
        'partner_id': fields.many2one('res.partner', u'Empresa', ondelete="restrict"),
        'doc_type': fields.char(u"Tipo de Factura", size=20),  # 001 Inicio para agrupador
        'date_invoice': fields.date(u"Fecha"),  # 001 Inicio para agrupador
        'base_impuesto': fields.float(u'Base impuesto', digits_compute=dp.get_precision('Account')),
        # importe total factura
        'base_linea': fields.float(u'Base línea', digits_compute=dp.get_precision('Account')),
        # Importe factura sin iva
        'fondo_rotatorio': fields.boolean(u'Fondo rotatorio'),
    }

    def init(self, cr):
        drop_view_if_exists(cr, 'retention_lines_list_report')
        cr.execute("""
            create or replace view retention_lines_list_report as (
                SELECT
                    ROW_NUMBER() OVER(ORDER BY invoice_id ASC) AS id,
                    id_objeto,
                    invoice_id,
                    nro_obligacion,
                    numero_factura,
                    no_interno_factura,
                    proveedor,
                    rut,
                    partner_id,
                    iva,
                    monto_retencion,
                    tipo,
                    state,
                    fondo_rotatorio,
                    doc_type,
                    date_invoice,
                    tipo_retencion,
                    importe_total,
                    importe_sin_iva,
                    base_impuesto,
                    base_linea,
                    currency_id
                FROM
                    (
                    SELECT
                        rl.id as id_objeto,
                        rl.invoice_id,
                        ai.nro_obligacion,
                        ai.number as numero_factura,
                        ai.nro_factura_grp as no_interno_factura,
                        rp.name as proveedor,
                        rp.nro_doc_rupe as rut,
                        rp.id as partner_id,
                        ret.name as iva,
                        -- rl.amount_ret as monto_retencion,
                        CASE
                            WHEN ret.base_compute='ret_tax' THEN rl.base_retax * ret.percent / 100
                            WHEN ret.base_compute='ret_line_amount' THEN rl.base_ret_line * ret.percent / 100
                        ELSE 0.0
                        END as monto_retencion,
                        'Siif' as tipo_retencion,
                        'ret_lines' as tipo,
                        ai.state,
                        --fondo rotatorio
                        CASE
                            WHEN t.codigo='P' THEN True
                        ELSE False
                        END as fondo_rotatorio,
                        CASE
                            WHEN ai.doc_type='opi_invoice' THEN 'Factura OPI'
                            WHEN ai.doc_type='obligacion_invoice' THEN 'Obligación'
                            WHEN ai.doc_type='3en1_invoice' THEN 'TresEnUno'
                        ELSE 'Factura'
                        END as doc_type,
                        ai.date_invoice as date_invoice,
                        ai.amount_total as importe_total,
                        ai.amount_untaxed as importe_sin_iva,
                        rl.base_retax as base_impuesto,
                        rl.base_ret_line as base_linea,
                        ai.currency_id
                    FROM account_retention_line_ret rlr
                    left join account_retention_line rl on rlr.account_ret_line_id = rl.id
                    inner join account_invoice ai on ai.id = rl.invoice_id
                    left join res_partner rp on rp.id = ai.partner_id
                    left join tipo_ejecucion_siif t on t.id = ai.siif_tipo_ejecucion
                    left join account_retention ret on ret.id = rlr.retention_id
                    where rl.amount_ret > 0
                    and ai.state in ('open','paid','forced','intervened','prioritized')
                    --2 Retenciones globales

                    UNION

                    SELECT
                        grl.id as id_objeto,
                        grl.invoice_id,
                        ai.nro_obligacion,
                        ai.number as numero_factura,
                        ai.nro_factura_grp as no_interno_factura,
                        rp.name as proveedor,
                        rp.nro_doc_rupe as rut,
                        rp.id as partner_id,
                        grl.name as iva,
                        grl.amount_ret_pesos as monto_retencion,
                        'Manual' as tipo_retencion,
                        'global' as tipo,
                        ai.state,
                        --fondo rotatorio
                        CASE
                            WHEN t.codigo='P' THEN True
                            ELSE False
                        END as fondo_rotatorio,
                        CASE
                            WHEN ai.doc_type='opi_invoice' THEN 'Factura OPI'
                            WHEN ai.doc_type='obligacion_invoice' THEN 'Obligación'
                            WHEN ai.doc_type='3en1_invoice' THEN 'TresEnUno'
                            ELSE 'Factura'
                        END as doc_type, ai.date_invoice as date_invoice,
                        ai.amount_total as importe_total,
                        ai.amount_untaxed as importe_sin_iva,
                        0.0 as base_impuesto,
                        0.0 as base_linea,
                        (select c.id from res_currency c where c.name = 'UYU') as currency_id
                        FROM account_global_retention_line grl
                        inner join account_invoice ai on ai.id = grl.invoice_id
                        left join tipo_ejecucion_siif t on t.id = ai.siif_tipo_ejecucion
                        left join res_partner rp on rp.id = ai.partner_id
                        where
                        grl.amount_ret_pesos > 0
                        and ai.state in ('open','paid','forced','intervened','prioritized')
                        --Retencion IRPF 7%

                    UNION

                    SELECT
                        rlrpf.id as id_objeto,
                        rlrpf.invoice_id,
                        ai.nro_obligacion,
                        ai.number as numero_factura,
                        ai.nro_factura_grp as no_interno_factura,
                        rp.name as proveedor,
                        rp.nro_doc_rupe as rut,
                        rp.id as partner_id,
                        ret.name as iva,
                        rlrpf.amount_ret as monto_retencion,
                        'IRPF' as tipo_retencion,
                        'ret_irpf' as tipo,
                        ai.state,
                        --fondo rotatorio
                        CASE
                            WHEN t.codigo='P' THEN True
                            ELSE False
                        END as fondo_rotatorio,
                        CASE
                            WHEN ai.doc_type='opi_invoice' THEN 'Factura OPI'
                            WHEN ai.doc_type='obligacion_invoice' THEN 'Obligación'
                            WHEN ai.doc_type='3en1_invoice' THEN 'TresEnUno'
                            ELSE 'Factura'
                        END as doc_type,
                        ai.date_invoice as date_invoice,
                        ai.amount_total as importe_total,
                        ai.amount_untaxed as importe_sin_iva,
                        --rl.base_amount as base_impuesto,
                        --rl.base_ret_line as base_linea,
                        --ai.currency_id
                        rlrpf.base_amount_pend as base_impuesto,
                        0.0 as base_linea,
                        ai.currency_id
                    FROM account_retention_line_irpf rlrpf
                    inner join account_invoice ai on ai.id = rlrpf.invoice_id
                    left join tipo_ejecucion_siif t on t.id = ai.siif_tipo_ejecucion
                    left join res_partner rp on rp.id = ai.partner_id
                    left join account_retention ret on ret.id = rlrpf.retention_id
                    where
                        rlrpf.amount_ret > 0
                        and ai.state in ('open','paid','forced','intervened','prioritized')
                    order by date_invoice desc)
                    as query1)"""
        )
