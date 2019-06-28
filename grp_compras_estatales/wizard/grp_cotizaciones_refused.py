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

from openerp import fields, models, api, _
from openerp.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

MOTIVE_REFUSED = [('cancel', 'Cancelar Adjudicación'),
                  ('change', 'Modificar Adjudicación')]


class grpCoreCotizacionRefused(models.TransientModel):
    _name = 'grp.cotizaciones.refused.wizard'
    _description = _('Rechazar')

    note = fields.Char(u'Observaciones sobre Cancelación / Modificación', size=80, required=True)
    motive = fields.Selection(MOTIVE_REFUSED, u'Motivo', required=True)

    @api.multi
    def save(self):
        if 'active_id' in self._context:
            cotizacion_id = self._context.get('active_id')
            for record in self:
                cot_obj = self.env['grp.cotizaciones'].browse(cotizacion_id)
                cot_obj.write(
                    {'motive': record.motive, 'note': record.note, 'state': 'refused'})
                # TODO: GAP 454 Spring 7
                Mail = self.pool['mail.mail']
                ir_model_data = self.env['ir.model.data']
                _model, group_id = ir_model_data.get_object_reference('grp_seguridad',
                                                                      'grp_compras_apg_Responsable_SIIF')
                users = self.env['res.users'].search([('groups_id', 'in', group_id),('operating_unit_ids','in',cot_obj.operating_unit_id.id)])
                partner_ids = []
                if users:
                    partner_ids = [user.partner_id.id for user in users]
                body = u'''
                       Se ha rechazado la adjudicación: %(name)s
                       por parte del ordenador del gasto por el motivo: %(motivo)s
                       ''' % {'name': cot_obj.name,
                              'motivo': u'Cancelar Adjudicación' if cot_obj.motive == 'cancel' else u'Modificar Adjudicación'}
                vals = {'state': 'outgoing',
                        'subject': 'Adjudicación rechazada',
                        'body_html': '<pre>%s</pre>' % body,
                        'recipient_ids': [(6, 0, partner_ids)],
                        'email_from': self.write_uid.email
                        }
                mail_id = self.env['mail.mail'].create(vals).id
                Mail.send(self._cr, self._uid, [mail_id], context=self._context)

        return True
