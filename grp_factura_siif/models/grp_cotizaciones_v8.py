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
from openerp import api, exceptions, fields, models
import openerp.addons.decimal_precision as dp
from operator import attrgetter
from lxml import etree
from openerp.osv.orm import setup_modifiers
from openerp.exceptions import Warning, ValidationError
from openerp.tools.translate import _
from presupuesto_estructura import TIPO_DOCUMENTO


# TODO: GAP 126 SPRING 6
class grpCoreCotizacionSiif(models.Model):
    _inherit = 'grp.cotizaciones'

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        res = super(grpCoreCotizacionSiif, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type,
                                                                 context=context,
                                                                 toolbar=toolbar, submenu=submenu)
        doc = etree.XML(res['arch'])
        if view_type == 'form':
            for field in res['fields']:
                node = doc.xpath("//field[@name='" + field + "']")[0]
                if field == 'estimate_ids':
                    readonly = (self.pool.get('res.users').has_group(cr, uid,
                                                                     'grp_seguridad.grp_compras_pc_Comprador')) or (
                               self.pool.get(
                                   'res.users').has_group(cr, uid, 'grp_seguridad.grp_compras_apg_Responsable_SIIF'))
                    node.set('readonly', '0' if readonly else '1')
                setup_modifiers(node, res['fields'][field])

        res['arch'] = etree.tostring(doc)
        return res

    # TODO Spring 6 GAP 126
    provider_ids = fields.One2many('grp.cotizaciones.proveedor.pesos', 'cot_id', string='Proveedor pesos')
    estimate_ids = fields.One2many('grp.cotizaciones.estimado.comprometer', 'cot_id', string='Estimado de comprometer')
    provider_compromise_ids = fields.One2many('grp.cotizaciones.compromiso.proveedor', 'cot_id', string='Compromisos')
    total_estimado = fields.Float(compute='get_total_pesos', string='Total estimado pesos',
                                  digits_compute=dp.get_precision('Cantidad'))

    # TODO Spring 7 GAP 440
    diff_apg_total_estimado = fields.Float(string="Diferencia entre APGs y total adjudicado",
                                           digits_compute=dp.get_precision('Cantidad'))

    partners_name = fields.Char('Nombre de proveedores', compute='_compute_partners_name', store=True)

    @api.multi
    @api.depends('provider_ids.provider_id')
    def _compute_partners_name(self):
        for rec in self:
            rec.partners_name = '; '.join([x.provider_id.name_get()[0][1] for x in rec.provider_ids])


    @api.multi
    def _set_provider_amount(self):
        for rec in self:
            rec.provider_ids.suspend_security().unlink()
            partner_dict = {}
            if len(rec.sice_page_aceptadas):
                for line in rec.sice_page_aceptadas:
                    if line.proveedor_cot_id.id not in partner_dict:
                        partner_dict[line.proveedor_cot_id.id] = {'total': 0}
                    partner_dict[line.proveedor_cot_id.id]['total'] += line.subtotal_pesos

            rec.suspend_security().write({'provider_ids': [(0, 0,
                                         {'provider_id': k, 'total_amount': round(v['total'])}) for k, v in
                                        partner_dict.iteritems()]})

    # TODO Spring 6 GAP 126
    @api.multi
    def _set_estimate(self):
        for rec in self:
            estimate = [(5,)]
            fiscalyear = False
            name_split = rec.name.split('-')
            if len(name_split) > 1:
                year = name_split[0]
                fiscalyear = self.env['account.fiscalyear'].search([('name', '=', year)]).id
            for line in rec.provider_ids:
                estimate.append((0, 0, {'fiscalyear_id': fiscalyear, 'provider_id': line.provider_id.id,
                                        'total_amount': round(line.total_amount)}))
            rec.suspend_security().write({'estimate_ids': estimate})

    # TODO Spring 6 GAP 126
    @api.multi
    def write(self, vals):
        _super = super(grpCoreCotizacionSiif, self).write(vals)
        if _super and vals.has_key('sice_page_aceptadas'):
            for rec in self:
                rec._set_provider_amount()
        return _super

    @api.model
    def create(self, vals):
        _super = super(grpCoreCotizacionSiif, self).create(vals)
        _super._set_provider_amount()
        return _super

    # TODO R Spring 6 GAP 126
    @api.multi
    def button_create_compromise(self):
        self.ensure_one()
        self.control_apg()
        return {
            'name': _("Crear compromiso"),
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'grp.cotizaciones.comprometer.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'domain': '[]',
            'context': {
                'cot_id': self.id,

            }
        }

    # TODO Spring 7 GAP 440
    # TODO: R GAP 440
    @api.multi
    def control_apg(self):
        for rec in self:
            monto_apg = 0
            apg_ids = set(
                rec.page_apg.filtered(lambda x: x.state not in ['desafectado', 'rechazado', 'anulada']).mapped(
                    lambda apg: apg.id))
            apg_obj = self.env['grp.compras.apg'].browse(list(apg_ids))
            for apg in apg_obj:
                if apg.state == 'afectado':
                    for llave in apg.llpapg_ids:
                        monto_apg += llave.importe
                else:
                    if apg.moneda.id != apg.company_currency_id.id:
                        monto_apg += apg.monto_fnc
                    else:
                        monto_apg += apg.monto_divisa
            if round(rec.total_estimado) > monto_apg:
                raise Warning(
                    u"Para poder Comprometer una adjudicación, deben estar creadas todas las APG, incluidas las de años futuros por el total de la adjudicación")
            rec.write({'diff_apg_total_estimado': monto_apg - round(rec.total_estimado)})
        return True

    # RAGU action para actualizar la diferencia con la apg
    @api.multi
    def action_update_diff_apg_total_estimado(self):
        for rec in self:
            monto_apg = 0
            apg_ids = set(
                rec.page_apg.filtered(lambda x: x.state not in ['desafectado', 'rechazado', 'anulada']).mapped(
                    lambda apg: apg.id))
            apg_obj = self.env['grp.compras.apg'].browse(list(apg_ids))
            for apg in apg_obj:
                if apg.state == 'afectado':
                    for llave in apg.llpapg_ids:
                        monto_apg += llave.importe
                else:
                    if apg.moneda.id != apg.company_currency_id.id:
                        monto_apg += apg.monto_fnc
                    else:
                        monto_apg += apg.monto_divisa
            rec.write({'diff_apg_total_estimado': monto_apg - round(rec.total_estimado)})
        return True

    @api.one
    def act_cotizaciones_validado(self):
        to_return = super(grpCoreCotizacionSiif, self).act_cotizaciones_validado()
        self._set_estimate()
        return to_return

    #MVARELA 02/02/2018 se comenta control. incidencia=2098 Error control monto comprometido
    # # TODO: SPRING 8 GAP 125
    # @api.multi
    # def cotizaciones_in_authorization(self):
    #     for rec in self:
    #         if rec.provider_compromise_ids:
    #             compromises = rec.provider_compromise_ids.filtered(lambda x: x.state == 'committed')
    #             if not compromises:
    #                 raise exceptions.ValidationError(
    #                     (u'Se debe comprometer alguno de los compromisos antes de continuar con el proceso.'))
    #     return super(grpCoreCotizacionSiif, self).cotizaciones_in_authorization()

    @api.constrains('estimate_ids')
    def _check_estimate_amount(self):
        for rec in self:
            provider_dict = {}
            for obj in rec.estimate_ids:
                if obj.provider_id.id not in provider_dict:
                    provider_dict[obj.provider_id.id] = 0
                provider_dict[obj.provider_id.id] += obj.total_amount
                provider = rec.provider_ids.filtered(lambda x: x.provider_id.id == obj.provider_id.id)
                if not len(provider) or provider.total_amount < provider_dict[obj.provider_id.id]:
                    raise exceptions.ValidationError(
                        u'La suma por proveedor-año fiscal no debe superar el total adjudicado por proveedor en pesos.')

    @api.multi
    @api.depends('provider_ids')
    def get_total_pesos(self):
        for rec in self:
            total_estimado = 0
            for provider in rec.provider_ids:
                total_estimado += round(provider.total_amount)
            rec.total_estimado = total_estimado



# TODO Spring 6 GAP 126
class grpCotizacionesLineasAceptadas(models.Model):
    _inherit = 'grp.cotizaciones.lineas.aceptadas'

    subtotal_pesos = fields.Float(compute='_get_subtotal_pesos', digits_compute=dp.get_precision('Account'),
                                  string='Subtotal pesos', store=True)

    @api.multi
    @api.depends('subtotal', 'currency')
    def _get_subtotal_pesos(self):
        for rec in self:
            rec.subtotal_pesos = rec.subtotal
            base_currency_id = rec.pedido_cot_id.company_currency_id.id
            if rec.currency.id != base_currency_id:
                dates = rec.currency.rate_ids.sorted(key=attrgetter('name'))
                rec.subtotal_pesos = rec.subtotal * dates[-1].rate_presupuesto if len(dates) else rec.subtotal


# TODO Spring 6 GAP 126
class grpCotizacionesProveedorPesos(models.Model):
    _name = 'grp.cotizaciones.proveedor.pesos'

    cot_id = fields.Many2one('grp.cotizaciones', 'Cotización')
    provider_id = fields.Many2one('res.partner', 'Proveedor')
    total_amount = fields.Float(digits_compute=dp.get_precision('Account'), string='Total estimado pesos proveedor')


# TODO Spring 6 GAP 126
class grpCotizacionesEstimadoComprometer(models.Model):
    _name = 'grp.cotizaciones.estimado.comprometer'

    cot_id = fields.Many2one('grp.cotizaciones', 'Cotización')
    fiscalyear_id = fields.Many2one('account.fiscalyear', 'Año fiscal')
    provider_id = fields.Many2one('res.partner', 'Proveedor')
    total_amount = fields.Float(digits_compute=dp.get_precision('Account'), string='Monto estimado a consumir')
    cot_provider_ids = fields.Many2many(comodel_name="res.partner", string='Proveedores', compute='_get_providers')

    # TODO R Spring 6 GAP 126
    @api.onchange('fiscalyear_id', 'total_amount', 'cot_id')
    def _onchange_fiscalyear_provider(self):
        domain = {
            'provider_id': [('id', 'in', self.cot_id.provider_ids.mapped(lambda x: x.provider_id.id))]
        }
        return {'domain': domain}

    @api.multi
    def _get_providers(self):
        for rec in self:
            rec.cot_provider_ids = [prov.provider_id.id for prov in rec.cot_id.provider_ids]

    _sql_constraints = [
        (
        'fp_unique', 'unique(cot_id,fiscalyear_id,provider_id)', u'Ya ha generado líneas para ese año fiscal-proveedor')
    ]


# TODO Spring 6 GAP 126
class grpCotizacionesCompromisosXProveedor(models.Model):
    _name = 'grp.cotizaciones.compromiso.proveedor'
    _inherit = ['mail.thread']

    _description = 'Compromiso por proveedor'

    name = fields.Char(u'Número', default='/')
    date = fields.Date("Fecha", required=True, default=lambda *a: fields.Date.today())
    nro_compromiso = fields.Integer(u'Nro Compromiso', readonly=True)
    total_number_comp = fields.Integer(u'Total a comprometer', readonly=False)
    cot_id = fields.Many2one('grp.cotizaciones', u'Número de adjudicación', readonly=True)
    fiscalyear_id = fields.Many2one('account.fiscalyear', u'Año fiscal', required=True, readonly=True)
    inciso_siif_id = fields.Many2one('grp.estruc_pres.inciso', 'Inciso', readonly=True)
    ue_siif_id = fields.Many2one('grp.estruc_pres.ue', 'Unidad ejecutora', readonly=True)
    apg_id = fields.Many2one('grp.compras.apg', 'APG', required=True, readonly=True)
    pc_id = fields.Many2one('grp.pedido.compra', 'Pedido de compra', readonly=True)
    provider_id = fields.Many2one('res.partner', 'Proveedor', required=True, readonly=True)
    nro_afectacion_siif = fields.Integer(u'Nro Afectación SIIF', help=u'Nro. de afectación SIIF', related='apg_id.nro_afectacion_siif', readonly=True)
    siif_tipo_ejecucion = fields.Many2one('tipo.ejecucion.siif', u'Tipo de ejecución',
                                          readonly=True, related='apg_id.siif_tipo_ejecucion')

    siif_concepto_gasto = fields.Many2one('presupuesto.concepto', string=u'Concepto del gasto',
                                          readonly=True, related='apg_id.siif_concepto_gasto')

    siif_financiamiento = fields.Many2one('financiamiento.siif', string=u'Fuente de financiamiento',
                                          readonly=True, related='apg_id.siif_financiamiento')

    siif_codigo_sir = fields.Many2one('codigo.sir.siif', string=u'Código SIR',
                                      readonly=True, related='apg_id.siif_codigo_sir')

    siif_nro_fondo_rot = fields.Many2one('fondo.rotatorio.siif', string=u'Nro doc. fondo rotatorio',
                                         readonly=True, related='apg_id.siif_nro_fondo_rot')

    siif_tipo_documento = fields.Many2one('tipo.documento.siif', string=u'Tipo de documento',
                                          domain=[('visible_documento_compromiso', '=', True)])
    siif_descripcion = fields.Text(string=u'Descripción SIIF', size=100)

    llpapg_ids = fields.One2many('grp.cotizaciones.compromiso.proveedor.llavep', 'compromiso_id',
                                 string=u'Llaves presupuestales')
    state = fields.Selection([('draft', 'Borrador'), ('committed', 'Comprometido'), ('recalled', 'Anulado en SIIF'),
                              ('anulado', u'Anulado')],
                             'Estado', size=86, readonly=True, default='draft')
    modif_compromiso_log_ids = fields.One2many('modif.cot_compromiso.siif.log', 'cotizacion_compromiso_id', 'Log')
    anulacion_siif_log_ids = fields.One2many('cot_compromiso.anulacion.siif.log', 'cotizacion_compromiso_id', 'Log anulaciones')
    nro_comp_sist_aux = fields.Char(u'Nro Compromiso Sist. aux')
    anulada_siif = fields.Boolean('Anulada en SIIF', default=False)
    total_llave = fields.Integer("Total llave presupuestal", compute='_compute_total_llave')
    siif_sec_compromiso = fields.Char(u'Secuencial compromiso')
    siif_ult_modif = fields.Integer(u'Última modificación')
    # TODO: R I 280
    total_comprometido = fields.Integer(u'Total comprometido', compute='_compute_total_comprometido', store=True)
    obligaciones_count = fields.Integer(compute='_obligaciones_count', string="Obligaciones")
    filtro_sir = fields.Char(string=u'Filtro código SIR', compute='_compute_filtro_sir')

    @api.multi
    @api.depends('inciso_siif_id','ue_siif_id','siif_financiamiento')
    def _compute_filtro_sir(self):
        for rec in self:
            #Si el financiamiento es 11 filtro solo por financiamiento
            if rec.siif_financiamiento and rec.siif_financiamiento.codigo.zfill(2) == '11':
                rec.filtro_sir = '_____' + rec.siif_financiamiento.codigo.zfill(2) + '__________'
            #Si tiene inciso_siif_id, ue_siif_id y financiamiento != 11, filtro por inciso, ue y financiamiento
            elif rec.inciso_siif_id and rec.ue_siif_id and rec.siif_financiamiento:
                rec.filtro_sir = rec.inciso_siif_id.inciso + rec.ue_siif_id.ue + rec.siif_financiamiento.codigo.zfill(2) + '__________'
            # Si no finaciamiento, o el financiamiento es != 11 y no tiene inciso_siif_id o ue_siif_id, no muestra nada
            else:
                rec.filtro_sir = 'xxxxxxxxxxxxxxx'

    def _obligaciones_count(self):
        for compromiso in self:
            compromiso.obligaciones_count = self.env['account.invoice'].search_count([('compromiso_proveedor_id', '=', compromiso.id)])

    @api.multi
    def view_obligaciones(self):
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.invoice',
            'domain': [('compromiso_proveedor_id', 'in', self.ids)]
        }

    @api.multi
    def action_anular(self):
        self.write({'state': 'anulado'})

    @api.multi
    @api.depends('modif_compromiso_log_ids.importe')
    def _compute_total_comprometido(self):
        for rec in self:
            rec.total_comprometido = sum(map(lambda x: x.importe, rec.modif_compromiso_log_ids))

    @api.depends("llpapg_ids.importe")
    def _compute_total_llave(self):
        for record in self:
            total = 0
            for llave in record.llpapg_ids:
                total += llave.importe
            record.total_llave = total

    @api.multi
    def action_llpapg_reload(self):
        for rec in self:
            rec.llpapg_ids.unlink()
            llpapg_data = []
            if rec.apg_id:
                for llavep in rec.apg_id.llpapg_ids:
                    llpapg_data.append((0, 0, {
                        'odg_id': llavep.odg_id.id,
                        'auxiliar_id': llavep.auxiliar_id.id,
                        'programa_id': llavep.programa_id.id,
                        'proyecto_id': llavep.proyecto_id.id,
                        'fin_id': llavep.fin_id.id,
                        'mon_id': llavep.mon_id.id,
                        'tc_id': llavep.tc_id.id,
                        'importe': llavep.importe,
                    }))
            rec.llpapg_ids = llpapg_data

    @api.multi
    def _check_llpapg_ids(self):
        for rec in self:
            if sum(map(lambda x: x.importe, rec.llpapg_ids)) != rec.total_number_comp:
                raise ValidationError(_('La suma de los importes de las Llaves Presupuestales no puede ser distinto que el Total Comprometido!'))

    @api.multi
    def compromiso_impactar_presupuesto(self):
        estructura_obj = self.env['presupuesto.estructura']
        for compromiso in self:
            if compromiso.llpapg_ids:
                for llave in compromiso.llpapg_ids:
                    estructura = estructura_obj.obtener_estructura(compromiso.fiscalyear_id.id,
                                                                   compromiso.apg_id.inciso_siif_id.inciso,
                                                                   compromiso.apg_id.ue_siif_id.ue,
                                                                   llave.programa, llave.proyecto, llave.mon, llave.tc,
                                                                   llave.fin, llave.odg, llave.auxiliar)
                    # Control 2: que no exista una estructura
                    if estructura is None:
                        desc_error = '(%s - %s - %s - %s - %s - %s - %s - %s - %s - %s)' % \
                                     (compromiso.fiscalyear_id.code, compromiso.inciso_siif_id.inciso, compromiso.ue_siif_id.ue,
                                      llave.odg, llave.auxiliar, llave.fin, llave.programa, llave.proyecto, llave.mon,
                                      llave.tc)
                        raise exceptions.ValidationError(u'No se encontró estructura con la llave presupuestal asociada al Compromiso: ' + desc_error)

                    # Control 3: que no alcance el disponible para el monto de la llave presupuestal
                    # if estructura.disponible < llave.importe:
                    #    raise osv.except_osv('Error', 'El disponible de la estructura no es suficiente para cubrir el importe de la llave presupuestal.')

                    res_comprometer = estructura_obj.comprometer(compromiso.id, TIPO_DOCUMENTO.COMPROMISO, llave.importe, estructura)

            else:
                raise exceptions.ValidationError(u'No existen llaves presupuestales asociada al compromiso.')
        return True

    @api.multi
    def compromiso_enviar_siif(self):
        generador_xml = self.env['grp.siif.xml_generator']
        siif_proxy = self.env['siif.proxy']
        for compromiso in self:
            if compromiso.siif_tipo_ejecucion and compromiso.siif_tipo_ejecucion.codigo == 'P' and not compromiso.siif_nro_fondo_rot:
                raise exceptions.ValidationError(u'Si el tipo de ejecución es Fondo Rotatorio, se debe cargar Nro. de Fondo Rotatorio.')
            if compromiso.provider_id.tipo_doc_rupe == '' or compromiso.provider_id.nro_doc_rupe == '':
                raise exceptions.ValidationError(u'El proveedor debe tener configurado tipo y número de documento de RUPE.')

            # se compromete contra el SIIF
            anio_fiscal = compromiso.fiscalyear_id and compromiso.fiscalyear_id.id or False
            nro_carga = self.env['ir.sequence'].with_context({'fiscalyear_id': anio_fiscal}).get('num_carga_siif') # AÑO-INCISO-UE
            nro_carga = nro_carga[4:]
            nro_comp_sist_aux = self.env['ir.sequence'].with_context({'fiscalyear_id': anio_fiscal}).get('sec.siif.compromiso')
            nro_comp_sist_aux = nro_comp_sist_aux[4:]

            # Control de no enviar campos de SICE si alguna de las llaves tiene exceptuado_sice = True
            enviar_datos_sice = False
            if compromiso.siif_financiamiento.exceptuado_sice or compromiso.siif_tipo_ejecucion.exceptuado_sice or compromiso.siif_concepto_gasto.exceptuado_sice:
                enviar_datos_sice = False
            else:
                objeto_gasto_obj = self.env['presupuesto.objeto.gasto']
                for llave_pres in compromiso.llpapg_ids:
                    objeto_gasto_ids = objeto_gasto_obj.search([('name', '=', llave_pres.odg),
                                                                ('auxiliar', '=', llave_pres.auxiliar)], limit=1)
                    if objeto_gasto_ids:
                        if not objeto_gasto_ids.exceptuado_sice:
                            enviar_datos_sice = True
                    else:
                        raise exceptions.ValidationError(u'No se encontró objeto del gasto con ODG %s, y Auxiliar %s.' %
                                                         (llave_pres.odg, llave_pres.auxiliar))

            xml_compromiso = generador_xml.gen_xml_cotizacion_compromiso(cotizacion_compromiso=compromiso, llaves_presupuestales=compromiso.llpapg_ids,
                                              importe=compromiso.total_llave, nro_carga=nro_carga, tipo_doc_grp='02',
                                              nro_modif_grp=0,
                                              tipo_modificacion='A',
                                              enviar_datos_sice=enviar_datos_sice,
                                              nro_comp_sist_aux=nro_comp_sist_aux)

            resultado_siif = siif_proxy.put_solic(xml_compromiso)

            # conversiones del xml resultado
            xml_root = etree.fromstring(resultado_siif)
            str_xml_list = xml_root.xpath("//*[local-name()='return']")
            str_xml = str_xml_list[0].text
            if str_xml.find('?>') != -1:
                str_xml = str_xml.split('?>')[1]
            xml_root = etree.fromstring(str_xml)

            dicc_modif = {}
            descr_error = ''
            for movimiento in xml_root.findall('movimiento'):
                if dicc_modif.get('nro_compromiso', None) is None and movimiento.find(
                        'nro_compromiso').text and movimiento.find('nro_compromiso').text.strip():
                    dicc_modif['nro_compromiso'] = movimiento.find('nro_compromiso').text
                if dicc_modif.get('resultado', None) is None and movimiento.find(
                        'resultado').text and movimiento.find('resultado').text.strip():
                    dicc_modif['resultado'] = movimiento.find('resultado').text
                if dicc_modif.get('siif_sec_compromiso', None) is None and movimiento.find(
                        'sec_compromiso').text and movimiento.find('sec_compromiso').text.strip():
                    dicc_modif['siif_sec_compromiso'] = movimiento.find('sec_compromiso').text
                if dicc_modif.get('siif_ult_modif', None) is None and movimiento.find(
                        'nro_modif_sist_aux').text and movimiento.find('nro_modif_sist_aux').text.strip():
                    dicc_modif['siif_ult_modif'] = movimiento.find('nro_modif_sist_aux').text
                if not descr_error and movimiento.find('comentario').text and len(movimiento.find('comentario').text) > 5:
                    descr_error = movimiento.find('comentario').text
                # MVARELA 07/01 Si viene E en alguno de los movimientos se larga el error
                if movimiento.find('resultado').text == 'E':
                    raise exceptions.ValidationError('Error al comprometer en SIIF: %s' %
                                                     (descr_error or u'Error no especificado por el SIIF'))
                if dicc_modif.get('nro_compromiso', False) and dicc_modif.get('nro_compromiso', False).strip() \
                        and dicc_modif.get('resultado', False):
                    break

            dicc_modif['nro_comp_sist_aux'] = nro_comp_sist_aux
            # 004 Pasa a Comprometido = True
            dicc_modif['anulada_siif'] = False
            res_write = compromiso.write(dicc_modif)

            if res_write:
                modif_compromiso_log_obj = self.env['modif.cot_compromiso.siif.log']
                for llave in compromiso.llpapg_ids:
                    vals = {
                        'cotizacion_compromiso_id': compromiso.id,
                        'tipo': 'A',
                        'fecha': fields.Date.today(),
                        'programa': llave.programa,
                        'proyecto': llave.proyecto,
                        'moneda': llave.mon,
                        'tipo_credito': llave.tc,
                        'financiamiento': llave.fin,
                        'objeto_gasto': llave.odg,
                        'auxiliar': llave.auxiliar,
                        'importe': llave.importe,
                        'siif_sec_compromiso': dicc_modif.get('siif_sec_compromiso', False),
                        'siif_ult_modif': dicc_modif.get('siif_ult_modif', False),
                    }
                    modif_compromiso_log_obj.create(vals)
        return True

    @api.multi
    def button_comprometer(self):
        self._check_llpapg_ids()
        integracion_siif = self.env.user.company_id.integracion_siif or False
        if integracion_siif and self.filtered(lambda r: r.nro_compromiso):
            raise ValidationError("Este documento ya ha sido enviado a SIIF. Por favor, actualice el navegador.")
        self.compromiso_impactar_presupuesto()
        if integracion_siif:
            self.compromiso_enviar_siif()
        self.write({'state': 'committed'})

        for rec in self:
            partner_ids = [partner.id for partner in rec.pc_id.message_follower_ids]

            msg = _(
                """
                Para la Adjudicación <a href="#action=mail.action_mail_redirect&amp;model=grp.cotizaciones&amp;res_id=%s">%s<a/>   correspondiente al
                pedido de compra <a href="#action=mail.action_mail_redirect&amp;model=grp.pedido.compra&amp;res_id=%s">%s<a/>, el compromiso
                <a href="#action=mail.action_mail_redirect&amp;model=grp.cotizaciones.compromiso.proveedor&amp;res_id=%s">%s<a/> está comprometido""") % (
                      rec.cot_id.id, rec.cot_id.name,rec.pc_id.id, rec.pc_id.name,rec.id, rec.name)

            self.pool.get('mail.thread').message_post(self._cr, self._uid, self.id, type="notification",
                                                  subtype='mt_comment', body=msg,
                                                  partner_ids=partner_ids)
        return True

    @api.multi
    def compromiso_cot_desafectar_presupuesto(self):
        estructura_obj = self.env['presupuesto.estructura']
        for compromiso in self:
            for llave in compromiso.llpapg_ids:
                estructura = estructura_obj.obtener_estructura(compromiso.fiscalyear_id.id,
                                                               compromiso.inciso_siif_id.inciso,
                                                               compromiso.ue_siif_id.ue,
                                                               llave.programa, llave.proyecto, llave.mon, llave.tc,
                                                               llave.fin, llave.odg, llave.auxiliar)
                # Control 2: que no exista una estructura
                if estructura is None:
                    desc_error = '(%s - %s - %s - %s - %s - %s - %s - %s - %s - %s)' % \
                                 (compromiso.fiscalyear_siif_id.code, compromiso.inciso_siif_id.inciso, compromiso.ue_siif_id.ue,
                                  llave.odg, llave.auxiliar, llave.fin, llave.programa, llave.proyecto, llave.mon, llave.tc)
                    raise exceptions.ValidationError(
                        u'No se encontró estructura con la llave presupuestal asociada al Compromiso: ' + desc_error)

                res_comprometer = estructura_obj.comprometer(compromiso.id, TIPO_DOCUMENTO.COMPROMISO, -1 * llave.importe, estructura)
                if not res_comprometer or not res_comprometer['codigo'] == 1:
                    raise exceptions.ValidationError(res_comprometer['mensaje'])
        return True

    @api.multi
    def compromiso_cot_desafectar_siif(self):
        generador_xml = self.env['grp.siif.xml_generator']
        siif_proxy = self.env['siif.proxy']
        for compromiso in self:
            if compromiso.siif_tipo_ejecucion and compromiso.siif_tipo_ejecucion.codigo == 'P' and not compromiso.siif_nro_fondo_rot:
                raise exceptions.ValidationError(u'Si el tipo de ejecución es Fondo Rotatorio, se debe cargar Nro. de Fondo Rotatorio.')
            if compromiso.provider_id.tipo_doc_rupe == '' or compromiso.provider_id.nro_doc_rupe == '':
                raise exceptions.ValidationError(u'El proveedor debe tener configurado tipo y número de documento de RUPE.')

            # Control de no enviar campos de SICE si alguna de las llaves tiene exceptuado_sice = True
            enviar_datos_sice = False
            if compromiso.siif_financiamiento.exceptuado_sice or compromiso.siif_tipo_ejecucion.exceptuado_sice or compromiso.siif_concepto_gasto.exceptuado_sice:
                enviar_datos_sice = False
            else:
                objeto_gasto_obj = self.env['presupuesto.objeto.gasto']
                for llave_pres in compromiso.llpapg_ids:
                    objeto_gasto_ids = objeto_gasto_obj.search([('name', '=', llave_pres.odg),
                                                                ('auxiliar', '=', llave_pres.auxiliar)], limit=1)
                    if objeto_gasto_ids:
                        if not objeto_gasto_ids.exceptuado_sice:
                            enviar_datos_sice = True
                    else:
                        raise exceptions.ValidationError(
                            u'No se encontró objeto del gasto con ODG %s, y Auxiliar %s.' %
                            (llave_pres.odg, llave_pres.auxiliar))

            # se compromete contra el SIIF
            anio_fiscal = compromiso.fiscalyear_id and compromiso.fiscalyear_id.id or False
            nro_carga = self.env['ir.sequence'].with_context({'fiscalyear_id': anio_fiscal}).get('num_carga_siif')  # AÑO-INCISO-UE
            nro_carga = nro_carga[4:]

            nro_modif = compromiso.siif_ult_modif + 1

            xml_anular_cot_compromiso = generador_xml.gen_xml_cotizacion_compromiso(cotizacion_compromiso=compromiso,
                                                                         llaves_presupuestales=compromiso.llpapg_ids,
                                                                         importe=compromiso.total_llave*-1,
                                                                         nro_carga=nro_carga, tipo_doc_grp='02',
                                                                         nro_modif_grp=nro_modif,
                                                                         tipo_modificacion='N',
                                                                         es_modif=True,
                                                                         motivo="Anulacion de compromiso",
                                                                         enviar_datos_sice=enviar_datos_sice,
                                                                         nro_comp_sist_aux=compromiso.nro_comp_sist_aux)

            resultado_siif = siif_proxy.put_solic(xml_anular_cot_compromiso)

            # conversiones del xml resultado
            xml_root = etree.fromstring(resultado_siif)
            str_xml_list = xml_root.xpath("//*[local-name()='return']")
            str_xml = str_xml_list[0].text
            if str_xml.find('?>') != -1:
                str_xml = str_xml.split('?>')[1]
            xml_root = etree.fromstring(str_xml)

            dicc_modif = {}
            descr_error = ''
            for movimiento in xml_root.findall('movimiento'):
                if dicc_modif.get('nro_compromiso', None) is None and movimiento.find('nro_compromiso').text and movimiento.find('nro_compromiso').text.strip():
                    dicc_modif['nro_compromiso'] = movimiento.find('nro_compromiso').text
                if dicc_modif.get('resultado', None) is None and movimiento.find('resultado').text and movimiento.find('resultado').text.strip():
                    dicc_modif['resultado'] = movimiento.find('resultado').text
                if dicc_modif.get('siif_sec_compromiso', None) is None and movimiento.find('sec_compromiso').text and movimiento.find('sec_compromiso').text.strip():
                    dicc_modif['siif_sec_compromiso'] = movimiento.find('sec_compromiso').text
                if dicc_modif.get('siif_ult_modif', None) is None and movimiento.find('nro_modif_sist_aux').text and movimiento.find('nro_modif_sist_aux').text.strip():
                    dicc_modif['siif_ult_modif'] = movimiento.find('nro_modif_sist_aux').text
                if not descr_error and movimiento.find('comentario').text and len(movimiento.find('comentario').text) > 5:
                    descr_error = movimiento.find('comentario').text
                # MVARELA 07/01 Si viene E en alguno de los movimientos se larga el error
                if movimiento.find('resultado').text == 'E':
                    raise exceptions.ValidationError('Error al anular compromiso en SIIF: %s' %
                                                     (descr_error or u'Error no especificado por el SIIF'))
                if dicc_modif.get('nro_compromiso', False) and dicc_modif.get('nro_compromiso',False).strip() and dicc_modif.get('resultado', False):
                    break

            anulacion_cot_compromiso_log_obj = self.env['cot_compromiso.anulacion.siif.log']
            # anulacion_siif_log_ids
            vals_history = {
                'cotizacion_compromiso_id': compromiso.id,
                'nro_afectacion_siif': compromiso.apg_id.nro_afectacion_siif or 0,
                'nro_compromiso': compromiso.nro_compromiso or 0,
                'nro_comp_sist_aux': compromiso.nro_comp_sist_aux or False,
            }
            anulacion_cot_compromiso_log_obj.create(vals_history)

            # Borrando valores
            if compromiso.modif_compromiso_log_ids:
                compromiso.modif_compromiso_log_ids.unlink()
            # Pasa a Comprometido = True
            dicc_modif.update({'nro_comp_sist_aux': False, 'nro_compromiso': False, 'anulada_siif': True})
            compromiso.write(dicc_modif)
        return True

    @api.multi
    def button_anular(self):
        self.compromiso_cot_desafectar_presupuesto()
        integracion_siif = self.env.user.company_id.integracion_siif or False
        if integracion_siif:
            self.compromiso_cot_desafectar_siif()
        self.write({'state': 'recalled'})
        return True


    @api.multi
    def abrir_wizard_modif_cot_compromiso_siif(self):
        mod_obj = self.env['ir.model.data']
        res = mod_obj.get_object_reference('grp_factura_siif', 'view_wizard_modif_cot_compromiso_siif')
        res_id = res and res[1] or False

        new_context = dict(self._context)
        new_context.update({
            'default_cot_compromiso_id': self.id,
            'default_ue_id': self.ue_siif_id.id
        })
        return {
            'name': "Modificaciones",  # Name You want to display on wizard
            'view_mode': 'form',
            'view_id': res_id,
            'view_type': 'form',
            'res_model': 'wiz.modificacion_cot_compromiso_siif',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': new_context,
        }

    @api.model
    def enviar_modificacion_siif(self, id):
        generador_xml = self.env['grp.siif.xml_generator']
        siif_proxy = self.env['siif.proxy']

        context = self._context
        programa = context['programa']
        proyecto = context['proyecto']
        moneda = context['moneda']
        tipo_credito = context['tipo_credito']
        tipo_modificacion = context['tipo_modificacion']
        financiamiento = context['financiamiento']
        objeto_gasto = context['objeto_gasto']
        auxiliar = context['auxiliar']
        importe = context['importe']
        fecha = context['fecha']
        motivo = context['motivo']
        auxiliar_id = context['auxiliar_id']
        fin_id = context['fin_id']
        mon_id = context['mon_id']
        odg_id = context['odg_id']
        programa_id = context['programa_id']
        proyecto_id = context['proyecto_id']
        tc_id = context['tc_id']

        cot_compromiso = self.browse(id)
        # MVARELA 15-09: Control de no enviar campos de SICE si alguna de las llaves tiene exceptuado_sice = True
        enviar_datos_sice = False
        if cot_compromiso.siif_financiamiento.exceptuado_sice or cot_compromiso.siif_tipo_ejecucion.exceptuado_sice or cot_compromiso.siif_concepto_gasto.exceptuado_sice:
            enviar_datos_sice = False
        else:
            objeto_gasto_obj = self.env['presupuesto.objeto.gasto']
            objeto_gasto_ids = objeto_gasto_obj.search([('name', '=', objeto_gasto),('auxiliar', '=', auxiliar)])
            if objeto_gasto_ids:
                if not objeto_gasto_ids[0].exceptuado_sice:
                    enviar_datos_sice = True
            else:
                raise exceptions.ValidationError(
                    u'No se encontró objeto del gasto con ODG %s, y Auxiliar %s.' % (objeto_gasto, auxiliar))

        lineas_llavep_obj = self.env['grp.cotizaciones.compromiso.proveedor.llavep']
        condicion = []
        condicion.append(('compromiso_id', '=', id))
        condicion.append(('programa', '=', programa))
        condicion.append(('proyecto', '=', proyecto))
        condicion.append(('odg', '=', objeto_gasto))
        condicion.append(('auxiliar', '=', auxiliar))
        condicion.append(('fin', '=', financiamiento))
        condicion.append(('mon', '=', moneda))
        condicion.append(('tc', '=', tipo_credito))
        llavep = lineas_llavep_obj.search(condicion, limit=1)
        if not llavep:
            if tipo_modificacion != 'A':
                raise exceptions.ValidationError(u'La llave presupuestal ingresada no se encuentra en el Compromiso.')
            else:
                vals = {
                    'compromiso_id': id,
                    'fin_id': fin_id,
                    'programa_id': programa_id,
                    'proyecto_id': proyecto_id,
                    'odg_id': odg_id,
                    'auxiliar_id': auxiliar_id,
                    'mon_id': mon_id,
                    'tc_id': tc_id,
                    'importe': 0,
                }
                llavep = lineas_llavep_obj.create(vals)


        if not cot_compromiso.nro_comp_sist_aux:
            raise exceptions.ValidationError(u'No puede enviar una modificación a SIIF sin Nro. de compromiso del sistema auxiliar.')

        # SE AFECTA CONTRA LA ESTRUCTURA LOCAL
        estructura_obj = self.env['presupuesto.estructura']
        estructura = estructura_obj.obtener_estructura(cot_compromiso.fiscalyear_id.id,
                                                       cot_compromiso.inciso_siif_id.inciso,
                                                       cot_compromiso.ue_siif_id.ue,
                                                       programa, proyecto, moneda, tipo_credito,
                                                       financiamiento, objeto_gasto, auxiliar)
        if estructura is None:
            desc_error = '(%s - %s - %s - %s - %s - %s - %s - %s - %s - %s)' % \
                         (cot_compromiso.fiscalyear_id.code, cot_compromiso.inciso_siif_id.inciso, cot_compromiso.ue_siif_id.ue,
                         objeto_gasto, auxiliar, financiamiento, programa, proyecto, moneda, tipo_credito)
            raise exceptions.ValidationError(u'No se encontró estructura con la llave presupuestal asociada al Compromiso: ' + desc_error)

        # ** Falta agregar controles **
        res = estructura_obj.comprometer(cot_compromiso.id, TIPO_DOCUMENTO.COMPROMISO, importe, estructura)

        if res['codigo'] == 1:
            # SE COMPROMETE CONTRA SIIF
            integracion_siif = self.env.user.company_id.integracion_siif or False
            if not integracion_siif:
                return True

            nro_carga = self.env['ir.sequence'].with_context(fiscalyear_id=cot_compromiso.fiscalyear_id.id).get('num_carga_siif')  # AÑO-INCISO-UE
            nro_carga = nro_carga[4:]
            nro_modif = cot_compromiso.siif_ult_modif + 1

            xml_modif_cot_compromiso = generador_xml.gen_xml_cotizacion_compromiso(cotizacion_compromiso=cot_compromiso,
                                                                    llaves_presupuestales=[llavep],
                                                                    importe=importe,
                                                                    nro_carga=nro_carga,
                                                                    tipo_doc_grp='02', nro_modif_grp=nro_modif,
                                                                    tipo_modificacion=tipo_modificacion, es_modif=True,
                                                                    motivo=motivo,
                                                                    nro_comp_sist_aux=cot_compromiso.nro_comp_sist_aux,
                                                                    enviar_datos_sice=enviar_datos_sice)

            resultado_siif = siif_proxy.put_solic(xml_modif_cot_compromiso)

            # conversiones del xml resultado
            xml_root = etree.fromstring(resultado_siif)
            str_xml_list = xml_root.xpath("//*[local-name()='return']")
            str_xml = str_xml_list[0].text
            if str_xml.find('?>') != -1:
                str_xml = str_xml.split('?>')[1]
            xml_root = etree.fromstring(str_xml)

            dicc_modif = {}
            descr_error = ''
            for movimiento in xml_root.findall('movimiento'):  # Es una lista si se afecta el mismo numero de carga una y otra vez
                if dicc_modif.get('nro_compromiso', None) is None:
                    dicc_modif['nro_compromiso'] = movimiento.find('nro_compromiso').text
                if dicc_modif.get('resultado', None) is None:
                    dicc_modif['resultado'] = movimiento.find('resultado').text
                if dicc_modif.get('siif_sec_compromiso', None) is None:
                    dicc_modif['siif_sec_compromiso'] = movimiento.find('sec_compromiso').text
                if dicc_modif.get('siif_ult_modif', None) is None:
                    dicc_modif['siif_ult_modif'] = movimiento.find('nro_modif_sist_aux').text
                if not descr_error and movimiento.find('comentario').text and len(movimiento.find('comentario').text) > 5:
                    descr_error = movimiento.find('comentario').text
                # MVARELA 07/01 Si viene E en alguno de los movimientos se larga el error
                if movimiento.find('resultado').text == 'E':
                    raise exceptions.ValidationError('Error al comprometer en SIIF: %s' % (descr_error or u'Error no especificado por el SIIF'))
                if dicc_modif.get('nro_compromiso', False) and dicc_modif.get('nro_compromiso',False).strip() and dicc_modif.get('resultado', False):
                    break

            cot_compromiso.write(dicc_modif)

            # Actualizar importe
            val_modif = {'importe': importe + llavep.importe}
            llavep.write(val_modif)

            modif_log_obj = self.env['modif.cot_compromiso.siif.log']
            vals = {
                'cotizacion_compromiso_id': cot_compromiso.id,
                'tipo': tipo_modificacion,
                'fecha': fecha,
                'programa': programa,
                'proyecto': proyecto,
                'moneda': moneda,
                'tipo_credito': tipo_credito,
                'financiamiento': financiamiento,
                'objeto_gasto': objeto_gasto,
                'auxiliar': auxiliar,
                'importe': importe,
                'siif_sec_compromiso': dicc_modif['siif_sec_compromiso'] if 'siif_sec_compromiso' in dicc_modif else False,
                'siif_ult_modif': dicc_modif['siif_ult_modif'] if 'siif_ult_modif' in dicc_modif else False,
            }
            modif_log_obj.create(vals)
        return True

class modifCotCompromisoSiifLog(models.Model):
    _name = 'modif.cot_compromiso.siif.log'
    _description = "Log de modificaciones de cotizaciones compromiso SIIF"

    cotizacion_compromiso_id = fields.Many2one('grp.cotizaciones.compromiso.proveedor', u'Cotización Compromiso', required=True)
    tipo = fields.Selection(
        (('A', u'A - Aumento'),
         ('R', u'R - Reducción')),
         # ('C', u'C - Corrección'),
         # ('N', u'N - Anulación'),
         # ('D', u'D - Devolución')),
         'Tipo')
    fecha = fields.Date('Fecha', required=True)
    importe = fields.Integer('Importe', required=True)
    programa = fields.Char('Programa', size=3, required=True)
    proyecto = fields.Char('Proyecto', size=3, required=True)
    moneda = fields.Char('MON', size=2, required=True)
    tipo_credito = fields.Char('TC', size=1, required=True)
    financiamiento = fields.Char('FF', size=2, required=True)
    objeto_gasto = fields.Char('ODG', size=3, required=True)
    auxiliar = fields.Char('AUX', size=3, required=True)
    siif_sec_compromiso = fields.Char(u'Secuencial compromiso')
    siif_ult_modif = fields.Integer(u'Última modificación')

class cotCompromisoAnulacionesSiifLog(models.Model):
    _name = 'cot_compromiso.anulacion.siif.log'
    _description = u"Log Cotización compromiso anulaciones"

    cotizacion_compromiso_id = fields.Many2one('grp.cotizaciones.compromiso.proveedor', u'Cotización Compromiso', required=True, ondelete='cascade')
    fecha = fields.Date('Fecha', default=lambda *a: fields.Date.today())
    nro_afectacion_siif = fields.Integer(u'Nro Afectación SIIF')
    nro_compromiso = fields.Char(u'Nro Compromiso')
    nro_comp_sist_aux = fields.Char(u'Nro Compromiso Sistema Aux')


class grpCoreCotizacionRefusedInherited(models.TransientModel):
    _inherit = 'grp.cotizaciones.refused.wizard'

    @api.multi
    def save(self):
        if 'active_id' in self._context:
            cotizacion_id = self._context.get('active_id')
            for record in self:
                cot_obj = self.env['grp.cotizaciones'].browse(cotizacion_id)
                for comp in cot_obj.provider_compromise_ids:
                    if comp.state not in ['anulado']:
                        raise exceptions.ValidationError(u'No puede cancelar la Adjudicación si tiene compromisos'
                                                         u' de proveedor sin anular.')
        return super(grpCoreCotizacionRefusedInherited, self).save()

