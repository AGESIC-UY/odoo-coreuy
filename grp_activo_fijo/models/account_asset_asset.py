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
from openerp import tools, SUPERUSER_ID, api,exceptions
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import calendar
from openerp.tools import float_is_zero
import pyqrcode
import io
import logging
import openerp.addons.decimal_precision as dp

_logger = logging.getLogger(__name__)

_FIRMA_UBICACION = [('ID', 'Angulo Inferior Derecho'), ('SD', 'Angulo Superior Derecho'),
                    ('II', 'Angulo Inferior Izquierdo'), ('SI', 'Angulo Superior Izquierdo'), ('O', 'Otro')]
_ESTADO_FIRMA = [('L', 'Legible'), ('I', 'Ilegible'), ('S', 'Sin firma')]
_SOPORTE = [('LT', 'Lienzo/Tela'), ('M', 'Madera'), ('P', 'Papel'), ('C', 'Cartón'), ('O', 'Otro')]
_MODO_ADQUISICION = [('G', u'Título gratuito'), ('O', u'Título oneroso')]
_ESTADO_HISTORIAL_RESP = [('AC', 'Aceptado'), ('EP', 'En proceso'), ('RE', 'Rechazado')]
_ESTADO_ACTIVO = [('B', 'Bueno'), ('R', 'Regular'), ('M', 'Malo')]
_TENENCIA_ACTIVO = [('propio', 'Propio-Adquirido'), ('propio_donado','Propio-Donado'), ('prestado', 'Prestado a'), ('en_prestamo', u'En préstamo de')]
_PROPIEDAD = [('inciso', 'Inciso'), ('arrendatario', 'Arrendatario'), ('comodatario', 'Comodatario')]
_ESTADO_INCISO = [('arrendamiento', 'Arrendamiento'), ('comodato', 'Comodato'), ('uso_inciso', 'Uso del Inciso')]

class account_asset_asset(osv.osv):
    _inherit = ['account.asset.asset', 'mail.thread']
    _name = 'account.asset.asset'
    _order = 'id desc'

    _mail_post_access = 'read'

    #dada la categoria del activo, obtiene los grupos asociados tomando en cuenta la unidad ejecutora
    def _get_partners_notification(self, cr, uid, asset_id, context=None):
        res_users_obj = self.pool.get('res.users')
        group_ids = []
        asset = self.browse(cr, uid, asset_id, context=context)
        for categoria in asset.category_id.categoria_ue_notificacion_ids:
            if categoria.operating_unit_id == asset.operating_unit_id and categoria.group_id.id not in group_ids:
                group_ids.append(categoria.group_id.id)
        user_ids = res_users_obj.search(cr, uid, [('groups_id', 'in', group_ids)], context=context)
        partner_ids = list(set(u.partner_id.id for u in res_users_obj.browse(cr, SUPERUSER_ID, user_ids, context=context)))
        return partner_ids

    def _default_category_ids(self, cr, uid, context=None):
        return self.pool.get('account.asset.category').search(cr, uid, [], context=context)

    def _es_resp(self, cr, uid, ids, object, arg, context=None):
        res = {}
        for activo in self.browse(cr, uid, ids, context=context):
            resultado = (uid == activo.user_id.id)
            res[activo.id] = resultado
            return res

    def _get_category_ids(self, cr, uid, ids, name, args, context=None):
        result = {}
        asset_category_obj = self.pool.get('account.asset.category')
        for rec in self.browse(cr, uid, ids):
            if rec.invoice_id.id:
                result[rec.id] = asset_category_obj.search(cr, uid, [('codigo','=',rec.category_id.codigo)], context=context)
            else:
                result[rec.id] = asset_category_obj.search(cr, uid, [], context=context)
        return result

    def _concatenar(self, cr, uid, ids, name, arg, context={}):
        result = {}
        for rec in self.browse(cr, uid, ids, context):
            if rec.state in ['open', 'close', 'baja']:
                result[rec.id] = str(rec.category_id.codigo) + " / " + rec.purchase_date[:4] + " / " + str(rec.secuencia_activo).zfill(4)
            else:
                result[rec.id] = False
        return result

    def _generar_qr(self, cr, uid, ids, field_name, args=None, context=None):

        res = {}
        # Armo la cadena para el QR con la url conteniendo el id, modelo y tipo de form
        web_base_url = self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url')
        for activo_rec in self.browse(cr, uid, ids, context):
            if activo_rec.numero_activo:
                str_registro_id = str(activo_rec.id)
                str_url = web_base_url + '/#id=' + str_registro_id + '&view_type=form&model=account.asset.asset'
                str_qr = activo_rec.name + '\n' + activo_rec.numero_activo + '\n' + '\n' + str_url
            else:
                str_qr = ''

            url = pyqrcode.create(str_qr)
            buffer = io.BytesIO()
            url.png(buffer, scale=2, module_color=[0, 0, 0, 128], background=[0xff, 0xff, 0xff])
            imagen = buffer.getvalue()

            res[activo_rec.id] = imagen
        return res

    def _generar_qr_url(self, cr, uid, ids, field_name, args=None, context=None):

        res = {}
        # Armo la cadena para el QR con la url conteniendo el id, modelo y tipo de form
        web_base_url = self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url')
        for activo_rec in self.browse(cr, uid, ids, context):
            if activo_rec.numero_activo:
                str_registro_id = str(activo_rec.id)
                str_url = web_base_url + '/#id=' + str_registro_id + '&view_type=form&model=account.asset.asset'

            else:
                str_url = ''

            url = pyqrcode.create(str_url)
            buffer = io.BytesIO()
            url.png(buffer, scale=2, module_color=[0, 0, 0, 128], background=[0xff, 0xff, 0xff])
            imagen = buffer.getvalue()

            res[activo_rec.id] = imagen
        return res


    @api.model
    def _default_res_country(self):
        return self.env['res.country'].search([('code','in',['UY','Uy','uy','uY'])], limit=1)

    @api.onchange('country_id')
    def _onchange_country_id(self):
        self.localidad = False
        self.country_state_id = False
        if self.country_id:
            return {
                'domain': {
                    'country_state_id': [('country_id','=',self.country_id.id)],
                    'localidad': [('country_id','=',self.country_id.id)]
                }
            }

    @api.onchange('country_state_id')
    def _onchange_country_state_id(self):
        self.localidad = False
        if self.country_state_id:
            return {
                'domain': {'localidad': [('country_id','=',self.country_id.id),('state_id','=',self.country_state_id.id)]}
            }

    @api.onchange('surface_mts2')
    def _onchange_surface_mts2(self):
        if len(str(self.surface_mts2)) > 9:
            self.surface_mts2 = False
            return {
                'warning': {'title': 'Error', 'message': u'Se superó la cantidad permitida de superficie'},
            }

    @api.onchange('cant_pasajero')
    def _onchange_cant_pasajero(self):
        if len(str(self.cant_pasajero)) > 3:
            self.cant_pasajero = False
            return {
                'warning': {'title': 'Error', 'message': u'Se superó la cantidad permitida de pasajeros'},
            }

    @api.depends('method_period','depreciation_line_ids','depreciation_line_ids.move_check','depreciation_line_ids.amount','depreciation_line_ids.depreciation_date')
    def _compute_amortizacion(self):
        for record in self:
            record.amortizacion = 0
            for line in record.depreciation_line_ids.search([('asset_id','=',record.id),('move_check','=',False)], limit=1, order='depreciation_date'):
                if record.method_period > 0:
                    record.amortizacion = line.amount / (record.method_period * 30)
                break

    @api.depends('depreciation_line_ids', 'depreciation_line_ids.depreciated_value', 'depreciation_line_ids.move_check', 'depreciation_line_ids.depreciation_date', 'amortizacion_ac_baja')
    def _compute_amortizacion_ac(self):
        for record in self:
            for line in record.depreciation_line_ids.search([('asset_id','=',record.id),('move_check','=',True)]):
                record.amortizacion_ac += line.amount
            record.amortizacion_ac += record.amortizacion_ac_baja

    @api.one
    @api.constrains('inf_fecha_ini','inf_fecha_fin')
    def _check_garantia(self):

        if self.inf_fecha_ini and self.inf_fecha_fin and (self.inf_fecha_ini > self.inf_fecha_fin):
            raise exceptions.ValidationError('La fecha de fin de la garantia no puede ser menor que la fecha de inicio')

    # 001-Inicio
    def _amount_residual(self, cr, uid, ids, name, args, context=None):
        # PCAR Se sustituye SUM(abs(l.debit-l.credit)) por abs(SUM(l.debit-l.credit)) en la consulta
        cr.execute("""SELECT
                l.asset_id as id, abs(SUM(l.debit-l.credit)) AS amount
            FROM
                account_move_line l
            WHERE
                l.asset_id IN %s GROUP BY l.asset_id """, (tuple(ids),))
        res = dict(cr.fetchall())
        for asset in self.browse(cr, uid, ids, context):
            company_currency = asset.company_id.currency_id.id
            current_currency = asset.currency_id.id
            amount = self.pool['res.currency'].compute(cr, uid, company_currency, current_currency, res.get(asset.id, 0.0), context=context)
            res[asset.id] = asset.purchase_value - amount - asset.salvage_value
        for id in ids:
            res.setdefault(id, 0.0)
        return res
    # 001-Fin

    _columns = {
        'secuencia_activo': fields.integer('Secuencia'),
        'numero_activo': fields.function(_concatenar, type='char', method=True, string=u'Número', store=True),
        'image_medium': fields.binary("Medium-sized photo"),
        # 'unidades_originales': fields.integer('Unidades originales', readonly=True, states={'draft': [('readonly', False)]}),
        # 'unidades_actuales': fields.integer('Unidades actuales', readonly=True, states={'draft': [('invisible', True)]}),
        'fecha_baja': fields.date('Fecha de baja', select="1", readonly=True, states={'draft': [('invisible', True)], 'open': [('invisible', True)]}),

        # 001-Inicio
        'name': fields.char('Name', size=50, required=True, select=1),
        'department_id': fields.many2one('hr.department', u'Ubicación', select="1", track_visibility='onchange'),
        'user_id': fields.many2one('res.users', u'Responsable de la dirección', select="1"),
        'estado_activo': fields.selection(_ESTADO_ACTIVO, 'Estado del activo', track_visibility='onchange'),
        'estado_responsable': fields.selection(_ESTADO_HISTORIAL_RESP, 'Estado responsable'),
        'es_resp': fields.function(_es_resp, string='Es responsable?', type="boolean"),
        'invoice_id': fields.many2one('account.invoice', 'Nro. factura GRP', select="1"),
        'domain_category_ids': fields.function(_get_category_ids, method=True, type='many2many', relation='account.asset.category', string=u'Lista domain categorías'),
        'tenencia': fields.selection(_TENENCIA_ACTIVO, 'Tenencia', track_visibility='onchange'),
        'prestado_a_de': fields.char('Prestado a/de', size=30),
        'nombre_contacto': fields.char('Nombre-Contacto responsable'),
        # PCARBALLO - Se agregan los campos Fecha y Valor de Alta
        'fecha_alta': fields.date('Fecha de alta'),
        'valor_alta': fields.float('Valor de alta'),
        # --------------------------------------------------------------------------------------------
        # Campos relativos a Obras de Arte
        # --------------------------------------------------------------------------------------------
        'obra_arte_fecha': fields.date("Fecha de la obra"),
        'obra_arte_propietario': fields.char('Propietario', size=240),
        'obra_arte_codigo': fields.char(u'Código', size=64),
        'obra_arte_categoria_id': fields.many2one('grp.cat_obras_arte', u'Categoría', ondelete='restrict'),
        'obra_arte_genero_id': fields.many2one('grp.gen_obras_arte', u'Género', ondelete='restrict'),
        'obra_arte_autor': fields.char(u'Autor', size=64),
        'obra_arte_firma': fields.char(u'Firma', size=64),
        'obra_arte_firma_ubicacion': fields.selection(_FIRMA_UBICACION, u'Ubicación de la firma'),
        'obra_arte_estado_firma': fields.selection(_ESTADO_FIRMA, u'Estado de la firma'),
        'obra_arte_forma_id': fields.many2one('grp.forma_obras_arte', u'Forma', ondelete='restrict'),
        'obra_arte_dimension_alto': fields.char('Alto', size=20),
        'obra_arte_dimension_ancho': fields.char('Ancho', size=20),
        'obra_arte_dimension_diametro': fields.char(u'Diámetro', size=20),
        # Campo etiqueta TECNICA (falta)
        'obra_arte_tecnicas_ids': fields.many2many('grp.etiquetas_obras_arte', 'grp_etiquetas_obras_activos_rel',
                                                   'asset_id', 'obra_tecnica_id', u'Técnica'),
        'obra_arte_soporte': fields.selection(_SOPORTE, 'Soporte'),
        'obra_arte_modo_adquisicion': fields.selection(_MODO_ADQUISICION, u'Modo de adquisición'),
        'obra_arte_para_restaurar': fields.boolean('Para restaurar'),
        # --------------------------------------------------------------------------------------------
        # Campos relativos a Informatica
        # --------------------------------------------------------------------------------------------
        'inf_nuc': fields.char('NUC', size=64),
        'inf_tipo_id': fields.many2one('grp.tipos_bien_informatica', u'Tipo', ondelete='restrict'),
        'inf_marca': fields.char('Marca', size=64),
        'inf_modelo': fields.char('Modelo', size=64),
        'inf_ip': fields.char('IP', size=15),
        'inf_serial_num': fields.char(u'Número de serie', size=64),
        'inf_garantia_duracion': fields.char(u'Duración', size=64),
        'inf_fecha_ini': fields.date('Fecha inicio'),
        'inf_fecha_fin': fields.date('Fecha fin'),
        # --------------------------------------------------------------
        # Separador Caracteristicas
        # --------------------------------------------------------------
        'inf_tipo_name': fields.related('inf_tipo_id', 'name', type="char", relation="grp.tipos_bien_informatica",
                                        string="Nombre tipo"),
        'inf_prestaciones': fields.many2one('grp.tipos_impresoras', 'Prestaciones', ondelete='restrict'),
        'inf_contador_pag': fields.integer(u'Contador pág.'),
        'inf_carac_fecha': fields.date('Fecha'),
        'inf_contador_tot': fields.integer('Contador total'),
        'inf_disco': fields.char('Disco', size=64),
        'inf_memoria': fields.char('Memoria', size=64),
        'inf_procesador': fields.char('Procesador', size=64),
        'amortizacion': fields.float(u'Amortización', compute="_compute_amortizacion", readonly=True),
        'amortizacion_ac': fields.float(u'Amortización Acumulada', compute="_compute_amortizacion_ac", readonly=True),
        'amortizacion_ac_baja': fields.float(u'Amortización Acumulada', copy=False, readonly=True),
        # --------------------------------------------------------------
        # Separador General FALTA
        # --------------------------------------------------------------
        'gral_atributo_1': fields.many2one('grp.atributos', 'Atributo', ondelete='restrict'),
        'gral_atributo_2': fields.many2one('grp.atributos', 'Atributo', ondelete='restrict'),
        'gral_atributo_3': fields.many2one('grp.atributos', 'Atributo', ondelete='restrict'),
        'gral_valor_1': fields.many2one('grp.valores_atributos', 'Valor', ondelete='restrict'),
        'gral_valor_2': fields.many2one('grp.valores_atributos', 'Valor', ondelete='restrict'),
        'gral_valor_3': fields.many2one('grp.valores_atributos', 'Valor', ondelete='restrict'),
        #Otros atributos
        'gral_otro_atributo1': fields.char('Atributo1', size=100),
        'gral_otro_atributo2': fields.char('Atributo2', size=100),
        # Es activo Padre?
        'es_padre': fields.boolean(u'Es activo padre?'),
        # MVARELA 26_03 - se modifican campos estandar para agregar track_visibility
        'note': fields.text('Note', track_visibility='onchange'),
        'state': fields.selection([('draft', 'Draft'), ('check', 'En revisión'), ('open', 'Running'),
                                   ('close', 'Amortizado'), ('baja', 'Dado de baja')], 'Status',
                                  required=True,
                                  help="When an asset is created, the status is 'Draft'.\n" \
                                       "If the asset is confirmed, the status goes in 'Running' and the depreciation lines can be posted in the accounting.\n" \
                                       "You can manually close an asset when the depreciation is over. If the last line of depreciation is posted, the asset automatically goes in that status.",
                                  track_visibility='onchange'),
        'purchase_value_date': fields.date(u'Fecha primera amortización'),

        #CAMPOS one2many y many2many
        # Historial Baja
        'historial': fields.one2many('grp.historial_baja_activo', 'grp_account_asset_id', 'Historial de baja'),
        # Historial Responsable
        'historial_resp': fields.one2many('grp.historial_responsable', 'hist_resp_id', 'Historial responsable'),
        #codigo QR
        'grafico_qr': fields.function(_generar_qr, type='binary', store=False),
        'grafico_qr_url':fields.function(_generar_qr_url, type='binary', store=False),
        # --------------------------------------------------------------------------------------------
        # Campos relativos a Inmuebles
        # --------------------------------------------------------------------------------------------
        # todo faltan los campos many2one con localidad y many2no con no_contrato pq dichas clases no se encuentran en el core
        'direction': fields.char(u'Dirección', size=60),
        'name_inmueble': fields.char('Nombre', size=40),
        'padron': fields.char(u'Nro. padrón', size=10),
        'property': fields.selection(_PROPIEDAD, 'Propiedad'),
        'state_inciso': fields.selection(_ESTADO_INCISO, 'Estado'),
        'surface_mts2': fields.integer(u'Superficie (mts2)', size=5),
        # 'contract_number': fields.char('Nro. contrato', size=200),
        'inventory_ids': fields.one2many("grp.account_asset_inventory_line", 'activo_id', string="Inventarios",
                                         domain=[('state', '=', 'validado')]),

        'country_id': fields.many2one('res.country', u'País', default=_default_res_country),
        'localidad': fields.many2one('grp.localidad','Localidad'),
        'country_state_id': fields.many2one('res.country.state', 'Departamento'),

        # -------------------------------------------------
        # Vehicles Fields
        # -------------------------------------------------
        # Puede cambiar si se usa fleet.vehicle
        'tipo_vehiculo': fields.selection([('auto', 'Auto'), ('camioneta', 'Camioneta'), ('minibus', 'Minibus')],
                                          string=u'Tipo de vehículo'),
        'cant_pasajero': fields.integer('Cantidad de pasajeros'),
        'cilindrada': fields.char('Cilindrada', size=20),
        'tipo_combustible': fields.char('Tipo de combustible', size=20),
        # 001-Inicio
        'value_residual': fields.function(_amount_residual, method=True,
                                          digits_compute=dp.get_precision('Account'), string='Residual Value'),
        # 001-Fin
    }

    _defaults = {
        # 'unidades_originales': 1,
        # 'unidades_actuales': 1,
        'estado_activo': 'B',
        # 'purchase_value_date': _default_purchase_value_date,
        'domain_category_ids': _default_category_ids,
        'property': 'inciso',
    }

    def onchange_inf_tipo_id(self, cr, uid, ids, inf_tipo_id, context=None):
        inf_tipo_name = False
        if inf_tipo_id:
            inf_tipo_name = self.pool.get('grp.tipos_bien_informatica').browse(cr, uid, inf_tipo_id, context).name
        return {'value': {'inf_tipo_name': inf_tipo_name}}

    def onchange_category_id(self, cr, uid, ids, category_id, context=None):
        res = super(account_asset_asset, self).onchange_category_id(cr, uid, ids, category_id, context=context)
        # MVARELA - Si el activo proviene de una factura, solo permite cambiar la subcategoria
        if len(ids) > 0 and category_id:
            activo = self.browse(cr, uid, ids[0], context)
            if activo.invoice_id:
                nuevo_codigo = self.pool.get('account.asset.category').browse(cr, uid, category_id, context=context).codigo
                if nuevo_codigo != activo.category_id.codigo:
                    res['value']['category_id'] = False
                    res['warning'] = {'title': 'Error',
                                      'message': u'Sólo puede cambiar la subcategoría del activo. Este activo fue generado a partir de una factura.'}
        return res

    def _default_purchase_value_date(self, cr, uid, context=None):
        ret = False
        if date.today().month >= 6:
            year_def = date.today().year
            ret = date(year_def, 12, 31)
        else:
            year_def = date.today().year
            ret = date(year_def, 06, 30)
        return ret.strftime('%Y-%m-%d')

    def aceptar_responsable(self, cr, uid, ids, context=None):
        super(account_asset_asset, self).write(cr, uid, ids, {'estado_responsable': 'AC'}, context=context)
        for activo in self.browse(cr, uid, ids, context):
            valores = {
                'department_id': activo.department_id.id,
                'user_id': activo.user_id.id,
                'estado_responsable': 'AC',
                'hist_resp_id': activo.id,
            }
            self.pool.get('grp.historial_responsable').create(cr, uid, valores, context)

    def rechazar_responsable(self, cr, uid, ids, context=None):
        super(account_asset_asset, self).write(cr, uid, ids, {'estado_responsable': 'RE'}, context=context)
        for activo in self.browse(cr, uid, ids, context):
            valores = {
                'department_id': activo.department_id.id,
                'user_id': activo.user_id.id,
                'estado_responsable': 'RE',
                'hist_resp_id': activo.id,
            }
            self.pool.get('grp.historial_responsable').create(cr, uid, valores, context)

    # MVARELA 07_01_2016: Al confirmar se llama a la funcion calcular
    def validate(self, cr, uid, ids, context=None):
        for activo in self.browse(cr, uid, ids, context):
            if not activo.es_padre:
                anio = datetime.strptime(activo.purchase_date, "%Y-%m-%d").date().year
                cat = activo.category_id
                codigo = cat.codigo
                company_id = activo.company_id.id
                cr.execute("""select max(secuencia_activo) from account_asset_asset a, account_asset_category ac
                  where a.category_id = ac.id
                  and ac.codigo = %s
                  and EXTRACT(YEAR FROM purchase_date) = %s
                  and a.company_id = %s """ % (codigo, anio, company_id))
                maxima = cr.fetchone()[0]
                if not maxima:
                    maxima = 0
                self.write(cr, uid, [activo.id], {'secuencia_activo': maxima + 1}, context=context)
        res = super(account_asset_asset, self).validate(cr, uid, ids, context=context)
        self.compute_depreciation_board(cr, uid, ids, context=context)
        return res

    def set_to_draft(self, cr, uid, ids, context=None):
        res = super(account_asset_asset, self).set_to_draft(cr, uid, ids, context=context)
        self.write(cr, uid, ids, {'secuencia_activo': 0}, context=context)
        return res

    # PCARBALLO
    def _compute_board_amount(self, cr, uid, asset, i, residual_amount, amount_to_depr, undone_dotation_number,
                              posted_depreciation_line_ids, total_days, depreciation_date, context=None):
        # by default amount = 0
        amount = 0
        if i == undone_dotation_number:
            amount = residual_amount
        else:
            if asset.method == 'linear':
                amount = amount_to_depr / (undone_dotation_number - len(posted_depreciation_line_ids))
                if asset.prorata:
                    amount = amount_to_depr / asset.method_number
                    days = total_days - float(depreciation_date.strftime('%j'))
                    fecha_compra = datetime.strptime(asset.purchase_date, '%Y-%m-%d')
                    fecha_valor = datetime.strptime(asset.purchase_value_date, '%Y-%m-%d')
                    days_first_time = fecha_valor - fecha_compra
                    month_days = calendar.monthrange(fecha_compra.year, fecha_compra.month)[1]
                    _logger.info("Days First Time: %s", days_first_time.days)
                    if i == 1:
                        # amount = (amount_to_depr / asset.method_number) / total_days * days
                        # amount = (asset.purchase_value / ((asset.method_number * asset.method_period))/total_days) * days_first_time.days
                        amount = (asset.purchase_value / (
                            (asset.method_number * asset.method_period)) / month_days) * days_first_time.days
                    elif i == undone_dotation_number:
                        amount = (amount_to_depr / asset.method_number) / total_days * (total_days - days)
            elif asset.method == 'degressive':
                amount = residual_amount * asset.method_progress_factor
                if asset.prorata:
                    days = total_days - float(depreciation_date.strftime('%j'))
                    if i == 1:
                        amount = (residual_amount * asset.method_progress_factor) / total_days * days
                    elif i == undone_dotation_number:
                        amount = (residual_amount * asset.method_progress_factor) / total_days * (total_days - days)
        return amount

    def compute_depreciation_board(self, cr, uid, ids, context=None):
        depreciation_lin_obj = self.pool.get('account.asset.depreciation.line')
        currency_obj = self.pool.get('res.currency')
        for asset in self.browse(cr, uid, ids, context=context):
            if asset.value_residual == 0.0:
                continue
            posted_depreciation_line_ids = depreciation_lin_obj.search(cr, uid, [('asset_id', '=', asset.id),
                                                                                 ('move_check', '=', True)],
                                                                       order='depreciation_date desc')
            old_depreciation_line_ids = depreciation_lin_obj.search(cr, uid, [('asset_id', '=', asset.id),
                                                                              ('move_id', '=', False)])
            if old_depreciation_line_ids:
                depreciation_lin_obj.unlink(cr, uid, old_depreciation_line_ids, context=context)

            amount_to_depr = residual_amount = asset.value_residual
            depreciation_date = datetime.strptime(asset.purchase_value_date, '%Y-%m-%d')
            day = depreciation_date.day
            month = depreciation_date.month
            year = depreciation_date.year
            total_days = (year % 4) and 365 or 366
            precision_digits = self.pool.get('decimal.precision').precision_get(cr, uid, 'Account')
            undone_dotation_number = self._compute_board_undone_dotation_nb(cr, uid, asset, depreciation_date,
                                                                            total_days, context=context)
            for x in range(len(posted_depreciation_line_ids), undone_dotation_number):
                i = x + 1
                amount = self._compute_board_amount(cr, uid, asset, i, residual_amount, amount_to_depr,
                                                    undone_dotation_number, posted_depreciation_line_ids, total_days,
                                                    depreciation_date, context=context)
                amount = round(amount,2)
                if float_is_zero(amount, precision_digits=precision_digits):
                    continue
                residual_amount -= amount
                vals = {
                    'amount': amount,
                    'asset_id': asset.id,
                    'sequence': i,
                    'name': str(asset.id) + '/' + str(i),
                    'remaining_value': residual_amount,
                    'depreciated_value': (asset.purchase_value - asset.salvage_value) - (residual_amount + amount),
                    'depreciation_date': depreciation_date.strftime('%Y-%m-%d'),
                }
                depreciation_lin_obj.create(cr, uid, vals, context=context)
                # Considering Depr. Period as months
                depreciation_date = (datetime(year, month, day) + relativedelta(months=+asset.method_period))
                day = depreciation_date.day
                month = depreciation_date.month
                year = depreciation_date.year
        return True

    def create(self, cr, uid, values, context=None):
        if 'image_medium' in values and values['image_medium']:
            mediana = tools.image_resize_image_medium(values['image_medium'])
            values['image_medium'] = mediana
        # if 'unidades_originales' in values:
        #     values['unidades_actuales'] = values['unidades_originales']
        if 'user_id' in values and values['user_id']:
            values['estado_responsable'] = 'AC'
        asset_id = super(account_asset_asset, self).create(cr, uid, values, context=context)
        # group_id = self._get_groups_by_category(cr, uid, asset_id, context)
        # res_users = self.pool['res.users']
        # user_ids = res_users.search(cr, uid, [('groups_id', 'in', group_id)], context=context)
        # partner_ids = list(set(u.partner_id.id for u in res_users.browse(cr, SUPERUSER_ID, user_ids, context=context)))
        partner_ids = self._get_partners_notification(cr, uid, asset_id, context=context)
        body = "Se ha creado un activo fijo, favor de ingresar los datos adicionales que\
                corresponden para que el mismo pueda ser dado de alta en el sistema"
        self.message_post(
            cr, uid, [asset_id],
            body=body,
            partner_ids=partner_ids, context=context)
        return asset_id

    def write(self, cr, uid, ids, values, context=None):
        if 'image_medium' in values and values['image_medium']:
            mediana = tools.image_resize_image_medium(values['image_medium'])
            values['image_medium'] = mediana
        # if 'unidades_originales' in values:
        #     values['unidades_actuales'] = values['unidades_originales']

        #TODO: Se debe revisar el tema que este procedimiento se está haciendo comparando solo con el primer valor
        if 'user_id' in values:
            # si estado responsable esta seteado, pregunto por el primero
            if len(ids) > 0 and self.browse(cr, uid, ids[0], context).estado_responsable:
                values['estado_responsable'] = 'EP'
            # al primero se lo marca como aceptado
            else:
                values['estado_responsable'] = 'AC'
        #---------------------------------------------------------------------------------------------------------
        #Llamado a super
        res = super(account_asset_asset, self).write(cr, uid, ids, values, context=context)
        if 'user_id' in values:
            for activo in self.browse(cr, uid, ids, context=context):
                valores = {
                    'department_id': activo.department_id.id,
                    'user_id': activo.user_id.id,
                    'estado_responsable': 'EP',
                    'hist_resp_id': activo.id,
                }
                self.pool.get('grp.historial_responsable').create(cr, uid, valores, context=context)
                if activo.state == 'open' and activo.estado_responsable == 'EP':
                    if activo.user_id:
                        body = "Tiene un activo asignado para aceptar."
                        self.message_post(cr, uid, ids, type="notification", subtype='mt_comment', body=body,
                                          partner_ids=[activo.user_id.partner_id.id], context=context)
        elif 'department_id' in values:
            for activo in self.browse(cr, uid, ids, context=context):
                self.pool.get('grp.historial_responsable').create(cr, uid, {
                    'department_id': activo.department_id.id,
                    'user_id': activo.user_id.id,
                    'estado_responsable': 'AC',
                    'hist_resp_id': activo.id,
                }, context=context)
        return res

    # def _check_unidades(self, cr, uid, ids, context=None):
    #     record = self.browse(cr, uid, ids, context=context)
    #     for data in record:
    #         if data.unidades_actuales > data.unidades_originales:
    #             return False
    #     return True
    #
    # _constraints = [(_check_unidades, u'Error: Las unidades actuales no pueden superar a unidades originales.',
    #                  ['unidades_originales', 'unidades_actuales'])]


class grp_historial_baja_activo(osv.osv):
    _name = 'grp.historial_baja_activo'
    _order = 'fecha_baja desc'

    @api.multi
    def open_account_move(self):
        self.ensure_one()
        _r = self.env.ref('account.action_move_line_form').read([])[0]
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'display_name': 'Asientos',
            'view_type': 'form',
            'name': 'Asientos',
            'target': 'current',
            'view_mode': 'form',
            'res_id': self.account_move_id.id
        }

    _columns = {
        'fecha_baja': fields.date('Fecha de baja', required=True, select="1"),
        'motivo_baja': fields.many2one('grp.motivos_baja', 'Motivo', select="1"),
        'descripcion_motivo': fields.char(u'Descripción', size=64),
        'nro_expediente': fields.char(u'Nro. de expediente', size=30, required=False),
        'grp_account_asset_id': fields.many2one('account.asset.asset', 'ID de historial de baja', required=True),
        'account_move_id': fields.many2one('account.move', 'Asiento contable', readonly=True)
    }

class grp_historial_responsable(osv.osv):
    _name = 'grp.historial_responsable'
    _description = 'Historial del responsable'
    _order = 'write_date desc'

    _columns = {
        'hist_resp_id': fields.many2one('account.asset.asset', 'Activo Fijo'),
        'department_id': fields.many2one('hr.department', u'Ubicación', select="1"),
        'user_id': fields.many2one('res.users', 'Responsable', select="1"),
        'write_date': fields.datetime(u'Fecha modificación', readonly=True),
        'write_uid': fields.many2one('res.users', 'Usuario', readonly=True),
        'estado_responsable': fields.selection(_ESTADO_HISTORIAL_RESP, 'Estado responsable'),
        'name': fields.related('hist_resp_id', 'name', type='char', string='Nombre'),
    }
