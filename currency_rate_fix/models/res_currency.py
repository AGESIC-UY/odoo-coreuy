# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.osv import osv
from openerp.exceptions import ValidationError

class ResCurrency(models.Model):
    _inherit = "res.currency"

    def _get_current_rate(self, cr, uid, ids, raise_on_no_rate=True, context=None):
        if context is None:
            context = {}
        res = {}

        date = context.get('date') or fields.Date.today()
        for id in ids:
            cr.execute('SELECT rate FROM res_currency_rate '
                       'WHERE currency_id = %s '
                       'AND name <= %s '
                       'ORDER BY name desc LIMIT 1',
                       (id, date))
            if cr.rowcount:
                res[id] = cr.fetchone()[0]
            elif not raise_on_no_rate:
                res[id] = 0
            else:
                currency = self.browse(cr, uid, id, context=context)
                raise osv.except_osv(_('Error!'), _("No currency rate associated for currency '%s' for the given period") % (currency.name))
        return res

class ResCurrencyRate(models.Model):
    _inherit = "res.currency.rate"

    name = fields.Date(default=lambda self: fields.Date.today())

    @api.constrains('name')
    def _check_currency_rate_date(self):
        for rec in self:
            rates = self.search([('id', '!=', rec.id),
                                 ('name', '=', rec.name),
                                 ('currency_id','=', rec.currency_id.id)])
            if rates:
                raise ValidationError(_(u'Only one currency rate per day allowed: %s') % (rec.name))
        return True
