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

import time, datetime
from openerp.osv import osv, fields
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp

class account_retention(osv.osv):

    STATES_VALUE = {'draft': [('readonly', False)]}

    _name = 'account.retention'
    _description = _('Retention documents') #Documentos de Retencion
    _order = 'date desc, name desc'

    _columns = {
        'name': fields.char(_('Nombre'), size=64, readonly=True,required=True,states=STATES_VALUE),
        'number': fields.char(_(u'Número'), size=64, readonly=True,states=STATES_VALUE),
        'base_compute': fields.selection([('ret_tax',u'Impuesto'),('ret_line_amount',u'Monto de línea')],
                                    string=u'Base de cálculo', required=True,
                                    help=u"Base de cálculo de retenciones. Cuando se calcula la retención sobre el impuesto. La base de cálculo es \'Impuesto\'. Si se calcula la retención sobre el importe es utilizado \'Monto de línea\'."),
        'date': fields.date(u'Fecha de creación', readonly=True,states=STATES_VALUE), # fecha emision
        'journal_id': fields.many2one('account.journal', u'Diario', readonly=True,required=True,states=STATES_VALUE),
        'state': fields.selection([('draft', u'Borrador'), ('done', u'Validado'), ('cancel', u'Cancelado')],
            'Estado', readonly=True), # Borrador, Anticipado, Validado, Cancelado
        'percent': fields.float(u'Porciento', digits_compute=dp.get_precision('Account'), help=u"Este campo es usado para establecer el porciento a retener. Ejemplo: Para establecer un 30% se establece el valor numérico correspondiente.",
                                readonly=True, required=True,states=STATES_VALUE),
        'account_id': fields.many2one('account.account', 'Account', required=True, domain=[('type','<>','view'), ('type', '<>', 'closed')], help="La cuenta a la cual se contabilizará la retención."),
        'es_irpf_porciento': fields.boolean(string="Es IRPF"),
    }

    _defaults = {
        'state': lambda *a:'draft',
        'date': lambda *a: datetime.date.today().strftime('%Y-%m-%d')
    }

    _sql_constraints = [
        ('unique_name_retention', 'unique(name)', _(u'El nombre de la retención debe ser único.')),
    ]

    def create(self, cr, user, vals, context=None):
        if context is None:
            context = {}
        context = dict(context)
        if 'percent' in vals and vals['percent']>0:
            ref_origen = context and context.has_key('origen') and context.get('origen',False) or False
            state_origen = context and context.has_key('state') and context.get('state',False) or False
            state = 'state' in vals and vals['state'] or False
            if ref_origen=='line_ret' and state_origen=='done' and state != 'done':
                vals.update({
                        'state': 'done',
                    })
            return super(account_retention,self).create(cr, user, vals, context=None)
        else:
            raise osv.except_osv(_(u'Error de validación!'), _(u"El porcentaje a retener debe ser mayor que cero !"))

    def write(self, cr, user, ids, vals, context=None):
        if context is None:
            context = {}
        context = dict(context)
        if 'percent' in vals and not vals['percent'] > 0:
            raise osv.except_osv(_(u'Error de validación!'), _(u"El porcentaje a retener debe ser mayor que cero !"))

        ref_origen = context and context.has_key('origen') and context.get('origen',False) or False
        state_origen = context and context.has_key('state') and context.get('state',False) or False
        state = 'state' in vals and vals['state'] or False
        if ref_origen=='line_ret' and state_origen=='done' and state != 'done':
            vals.update({
                    'state': 'done',
                })
        return super(account_retention,self).write(cr, user, ids, vals, context=None)

    def button_validate(self, cr, uid, ids, context=None):
        """
        Botón de validación de Retención que se usa cuando
        se creó una retención manual, esta se relacionará
        con la factura seleccionada.
        """
        if context is None:
            context = {}
        context = dict(context)
        for ret in self.browse(cr, uid, ids, context):
            self.action_validate(cr, uid, [ret.id], context=context)
        return True

    def action_validate(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        for rec in self.browse(cr, uid, ids):
            number = context.get('number', False)
            if not number:
                number = rec.name
            self.write(cr, uid, rec.id, {'state': 'done', 'number': number})
            self.log(cr, uid, rec.id, ("The retention %s it generated with number: ") % number) #La retención %s fue generada.
        return True

    def action_cancel(self, cr, uid, id, *args):
        self.write(cr, uid, id, {'state': 'cancel'})
        return True

    def action_cancel_draft(self, cr, uid, id, *args):
        ret = self.browse(cr, uid, id)
        number = '/'
        self.write(cr, uid, id, {'state': 'draft', 'number': number})
        self.log(cr, uid, id, _("The retention %s it change state: ") % ret[0].number) #La retención %s fue generada.
        return True

account_retention()

