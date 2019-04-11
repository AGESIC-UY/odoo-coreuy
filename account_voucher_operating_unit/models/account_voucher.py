# -*- coding: utf-8 -*-
# © 2015 Eficent Business and IT Consulting Services S.L.
# - Jordi Ballester Alomar
# © 2015 Ecosoft Co. Ltd. - Kitti Upariphutthiphong
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from openerp import api, fields, models, _
from openerp.exceptions import ValidationError


class AccountVoucher(models.Model):
    _inherit = "account.voucher"

    @api.multi
    def _get_default_operating_unit(self):
        user = self.env['res.users'].browse(self._uid)
        return user.default_operating_unit_id

    operating_unit_id = fields.Many2one(
        'operating.unit',
        string='Operating Unit',
        default=_get_default_operating_unit,
    )

    # #Se vuelve atras el cambio porque hay casos donde no quieren que sea readonly
    # operating_unit_id = fields.Many2one('operating.unit', string='Operating Unit', related='journal_id.operating_unit_id',
    #                                     store=True, readonly=True)

    #Actualizo la operating_unit_id cada vez que se modifica el diario
    def onchange_journal(self, cr, uid, ids, journal_id, line_ids, tax_id, partner_id, date, amount, ttype, company_id, context=None):
        to_return = super(AccountVoucher, self).onchange_journal(cr, uid, ids, journal_id, line_ids, tax_id, partner_id, date, amount, ttype, company_id, context=context)
        if to_return and journal_id:
            operating_unit_id = self.pool.get('account.journal').browse(cr, uid, journal_id).operating_unit_id.id
            to_return['value'].update({
                'operating_unit_id': operating_unit_id,
            })
        return to_return

    @api.multi
    @api.constrains('operating_unit_id', 'company_id')
    def _check_company_operating_unit(self):
        for rec in self:
            if rec.company_id and rec.operating_unit_id and \
                    rec.company_id != rec.operating_unit_id.company_id:
                raise ValidationError(_('The Company in the Move Line and in '
                                        'the Operating Unit must be the same.'
                                        ))

    def account_move_get(self, cr, uid, voucher_id, context=None):
        move = super(AccountVoucher, self).account_move_get(cr, uid, voucher_id, context=context)
        voucher = self.pool.get('account.voucher').browse(cr, uid, voucher_id, context)
        if not voucher.operating_unit_id:
            return move
        else:
            if voucher.operating_unit_id:
                move['operating_unit_id'] = voucher.operating_unit_id.id
            else:
                raise ValidationError(_('The Voucher must have an Operating '
                                        'Unit.'))
        return move


class AccountVoucherLine(models.Model):
    _inherit = "account.voucher.line"

    # #TODO: no debe ser related al voucher, puede tener distintos valores
    # operating_unit_id = fields.Many2one(
    #     'operating.unit',
    #     related='voucher_id.operating_unit_id',
    #     string='Operating Unit', readonly=True,
    #     store=True,
    # )

    #TODO: es readonly?
    operating_unit_id = fields.Many2one('operating.unit', string='Operating Unit')

    # #TODO: REVISAR este metodo
    # @api.model
    # def create(self, vals):
    #     if 'operating_unit_id' not in vals:
    #         voucher = self.env['account.voucher'].browse(vals['voucher_id'])
    #         if voucher.operating_unit_id:
    #             vals['operating_unit_id'] = voucher.operating_unit_id.id
    #     return super(AccountVoucherLine, self).create(vals)
