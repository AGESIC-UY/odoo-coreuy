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
from openerp.tools.translate import _
import time

import logging

_logger = logging.getLogger(__name__)

class grp_set_def_cur_rate_type(osv.osv):
    _inherit = "res.currency.rate"

    _columns = {
        'rate_presupuesto': fields.float('Tipo cambio presupuesto', digits=(12, 6), help='Tipo de cambio para enviar al SIIF'),
        'rate_arbitraje': fields.float('Arbitraje', digits=(12, 6), help='Tipo de cambio arbitraje'), #001 Arbitraje
    }

    _defaults = {
        'rate_presupuesto': 1,
        'rate_arbitraje': 1,
    }

grp_set_def_cur_rate_type()

class grp_calcular_arbitraje(osv.osv):
    _inherit = "res.currency"

    def _current_rate_presupuesto(self, cr, uid, ids, name, arg, context=None):
        raise_on_no_rate= False
        if context is None:
            context = {}
        res = {}

        if 'date' in context:
            date = context.get('date')
        else:
            date = time.strftime('%Y-%m-%d')
        date = date or time.strftime('%Y-%m-%d')

        for id in ids:
            cr.execute('SELECT rate_presupuesto FROM res_currency_rate '
                       'WHERE currency_id = %s '
                         'AND name::date <= %s '
                       'ORDER BY name desc LIMIT 1',
                       (id, date))
            if cr.rowcount:
                res[id] = cr.fetchone()[0]
            elif not raise_on_no_rate:
                res[id] = 0
            else:
                currency = self.browse(cr, uid, id, context=context)
                raise osv.except_osv(_('Error!'),_("No currency rate associated for currency %d for the given period" % (id)))
        return res

    #001 Arbitraje
    def _current_rate_arbitraje(self, cr, uid, ids, name, arg, context=None):

        raise_on_no_rate= False
        if context is None:
            context = {}
        res = {}

        if 'date' in context:
            date = context.get('date')
        else:
            date = time.strftime('%Y-%m-%d')
        date = date or time.strftime('%Y-%m-%d')

        for id in ids:
            cr.execute('SELECT rate_arbitraje FROM res_currency_rate '
                       'WHERE currency_id = %s '
                         'AND name::date <= %s '
                       'ORDER BY name desc LIMIT 1',
                       (id, date))
            if cr.rowcount:
                res[id] = cr.fetchone()[0]
            elif not raise_on_no_rate:
                res[id] = 0
            else:
                currency = self.browse(cr, uid, id, context=context)
                raise osv.except_osv(_('Error!'),_("No currency rate associated for currency %d for the given period" % (id)))
        return res
    #001 Fin arbitraje

    def _get_conversion_rate(self, cr, uid, from_currency, to_currency, context=None):
        if context is None:
            context = {}
        ctx = context.copy()
        from_currency = self.browse(cr, uid, from_currency.id, context=ctx)
        to_currency = self.browse(cr, uid, to_currency.id, context=ctx)

        pricelist_type = context.get('pricelist_type', False) or 'sale'  # pricelist_type default to 'sale' and use buying rate
        to_currency_rate = 0.0
        from_currency_rate = 0.0
        # kittiu: Buying rate
        if pricelist_type == 'sale':
            if from_currency.rate == 0 or to_currency.rate == 0:
                date = context.get('date', time.strftime('%Y-%m-%d'))
                if from_currency.rate == 0:
                    currency_symbol = from_currency.symbol
                else:
                    currency_symbol = to_currency.symbol
                raise osv.except_osv(_('Error'), _('No buying rate found \n' \
                        'for the currency: %s \n' \
                        'at the date: %s') % (currency_symbol, date))
            to_currency_rate = to_currency.rate
            from_currency_rate = from_currency.rate
        # kittiu: Selling rate
        if pricelist_type == 'purchase':
            if from_currency.rate_sell == 0 or to_currency.rate_sell == 0:
                date = context.get('date', time.strftime('%Y-%m-%d'))
                if from_currency.rate == 0:
                    currency_symbol = from_currency.symbol
                else:
                    currency_symbol = to_currency.symbol
                raise osv.except_osv(_('Error'), _('No selling rate found \n' \
                        'for the currency: %s \n' \
                        'at the date: %s') % (currency_symbol, date))
            to_currency_rate = to_currency.rate_sell
            from_currency_rate = from_currency.rate_sell
        if pricelist_type == 'presupuesto':
            if from_currency.rate_presupuesto == 0 or to_currency.rate_presupuesto == 0:
                date = context.get('date', time.strftime('%Y-%m-%d'))
                if from_currency.rate == 0:
                    currency_symbol = from_currency.symbol
                else:
                    currency_symbol = to_currency.symbol
                raise osv.except_osv(_('Error'), _(u'No se encontró tipo de cambio de presupuesto '
                                                   u'para la moneda: %s '
                                                   u'en la fecha: %s') % (currency_symbol, date))
            to_currency_rate = to_currency.rate_presupuesto
            from_currency_rate = from_currency.rate_presupuesto
        if pricelist_type == 'arbitraje':
            if from_currency.rate_arbitraje == 0 or to_currency.rate_arbitraje == 0:
                date = context.get('date', time.strftime('%Y-%m-%d'))
                if from_currency.rate == 0:
                    currency_symbol = from_currency.symbol
                else:
                    currency_symbol = to_currency.symbol
                raise osv.except_osv(_('Error'), _(u'No se encontró tipo de cambio de arbitraje '
                                                   u'para la moneda: %s '
                                                   u'en la fecha: %s') % (currency_symbol, date))
            to_currency_rate = to_currency.rate_arbitraje
            from_currency_rate = from_currency.rate_arbitraje
        # kittiu: check Smaller/Bigger currency
        to_rate = to_currency.type_ref_base == 'bigger' and (1 / to_currency_rate) or to_currency_rate
        from_rate = from_currency.type_ref_base == 'bigger' and (1 / from_currency_rate) or from_currency_rate
        return to_rate / from_rate


    _columns = {
        'rate_presupuesto': fields.function(_current_rate_presupuesto, string='Tipo cambio presupuesto', digits=(12, 6),
            help='El tipo de cambio para presupuesto.'),
        'rate_arbitraje': fields.function(_current_rate_arbitraje, string='Arbitraje', digits=(12, 6),
            help='El tipo de cambio arbitraje.'), #001 Arbitraje
    }
grp_calcular_arbitraje()