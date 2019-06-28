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

from openerp.osv import fields, osv
from openerp.tools.translate import _


class res_currency(osv.osv):
    _inherit = 'res.currency'

    def _current_rate_sell(self, cr, uid, ids, name, arg, context=None):
        if context is None:
            context = {}
        res = {}
        if 'date' in context:
            date = context['date']
        else:
            date = time.strftime('%Y-%m-%d')
        date = date or time.strftime('%Y-%m-%d')
        # Convert False values to None ...
        for id in ids:
            cr.execute("SELECT currency_id, rate_sell "
                       "FROM res_currency_rate "
                       "WHERE currency_id = %s "
                       "AND name <= %s "
                       "ORDER BY name desc "
                       "LIMIT 1" ,(id, date))
            if cr.rowcount:
                id, rate = cr.fetchall()[0]
                res[id] = rate
            else:
                raise osv.except_osv(_('Error!'), _("No currency selling rate associated for currency %d for the given period" % (id)))
        return res

    def _current_rate(self, cr, uid, ids, name, arg, context=None):
        return super(res_currency, self)._current_rate(cr, uid, ids, name, arg, context=context)

    def _current_rate_silent(self, cr, uid, ids, name, arg, context=None):
        return super(res_currency, self)._current_rate_silent(cr, uid, ids, name, arg, context=context)

    _columns = {
        'type_ref_base': fields.selection([
            ('smaller', 'Smaller than base currency'),
            ('bigger', 'Bigger than base currency'),
            ], 'Type', required=True,
            help="""* If this currency is smaller, amount currency = amount base * rate
* If this currency is bigger, amount currency = amount base / rate
            """),
        'rate_sell': fields.function(_current_rate_sell, string='Current Selling Rate', digits=(12, 6),
            help='The rate of the currency to the currency of rate 1.'),
        'descripcion_iso': fields.char(u'Descripción', size=64),

        # irabaza NOTE: We must redefine fields ´´rate´´ and ´´rate_silent´´ in order to change precision digits
        #               equal to defined in ´´rate´´ field in model ´´res.currency.rate´´
        'rate': fields.function(_current_rate, string='Current Rate', digits=(12,6),
            help='The rate of the currency to the currency of rate 1.'),
        'rate_silent': fields.function(_current_rate_silent, string='Current Rate', digits=(12,6),
            help='The rate of the currency to the currency of rate 1 (0 if no rate defined).'),
    }
    _defaults = {
        'type_ref_base': 'smaller',
    }

    # A complete override method
    # Added Selling / Buying Rates
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
        # kittiu: check Smaller/Bigger currency
        to_rate = to_currency.type_ref_base == 'bigger' and (1 / to_currency_rate) or to_currency_rate
        from_rate = from_currency.type_ref_base == 'bigger' and (1 / from_currency_rate) or from_currency_rate
        return to_rate / from_rate

res_currency()


class res_currency_rate(osv.osv):

    _inherit = 'res.currency.rate'

    _columns = {
        'rate': fields.float('Buying Rate', digits=(12, 6), help='The selling rate of the currency to the currency of rate 1'),
        'rate_sell': fields.float('Selling Rate', digits=(12, 6), help='The purchase rate of the currency to the currency of rate 1'),
    }
    _defaults = {
        'rate_sell': 1,
    }
res_currency_rate()

