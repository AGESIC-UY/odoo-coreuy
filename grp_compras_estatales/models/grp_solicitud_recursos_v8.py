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

from openerp import models, fields, api, _, exceptions
import logging

class grp_solicitud_recursos_v8(models.Model):
    _inherit = 'grp.compras.solicitud.recursos.almacen'
    _name = 'grp.compras.solicitud.recursos.almacen'

    operating_unit_id = fields.Many2one(
        comodel_name='operating.unit',
        string='Unidad ejecutora responsable',
        required=True,
        default=lambda self: (self.env['res.users'].operating_unit_default_get(self.env.uid))
    )
    ## Performance reasons
    #product_validos_ids = fields.Many2many(comodel_name="product.product", compute="_get_products",
    #                                       string="Productos permitidos")
    lineas_readonly = fields.Boolean("Linea editables", compute='_compute_lineas_readonly', default=False)

    attachment_ids = fields.Many2many(compute='get_attachments_docs',
                                      comodel_name='ir.attachment',
                                      string=u'Documentos asociados')
    show_buttons_compra_stock = fields.Boolean(compute="_compute_show_buttons_compra_stock")
    pedidos_count = fields.Integer(string='Cantidad de pedidos', compute="_pedidos_count", search='_search_pedidos_count')

    @api.one
    def _pedidos_count(self):
        scs = self.env['grp.solicitud.compra'].search([('solicitud_recursos_id', '=', self.id)])
        line_pcs = self.env['grp.linea.pedido.compra'].search([('solicitud_compra_id', 'in', scs.ids)])
        pedido_ids = set(line.pedido_compra_id.id for line in line_pcs)
        self.pedidos_count = len(pedido_ids)

    def _search_pedidos_count(self, operator, value):
        _sql = """  SELECT sr.id
                    FROM grp_compras_solicitud_recursos_almacen sr
                        left join grp_solicitud_compra sc ON (sc.solicitud_recursos_id=sr.id)
                        left join grp_linea_pedido_compra lpc ON (lpc.solicitud_compra_id=sc.id)
                    GROUP BY sr.id
                    HAVING COUNT(DISTINCT lpc.pedido_compra_id) %s %%s """ % (operator)
        self._cr.execute(_sql, (value or 0,))
        sr_ids = [ x[0] for x in self._cr.fetchall() ]
        return [('id', 'in', sr_ids)]

    @api.one
    @api.depends('grp_sr_id','grp_sr_id.product_id','grp_sr_id.product_id.type','grp_sr_id.product_id.no_inventory')
    def _compute_show_buttons_compra_stock(self):
        inv_buttons = all(line.product_id and (line.product_id.type=='service' or (line.product_id.type=='consu' and line.product_id.no_inventory)) for line in self.grp_sr_id)
        self.show_buttons_compra_stock = not inv_buttons

    ## Performance reasons
    ## See: product.product name_search
    #@api.depends('tipo_sr')
    #def _get_products(self):
    #    for record in self:
    #        tipo_sr = record.tipo_sr
    #       domain = [('purchase_ok','=',True)]
    #       if tipo_sr == 'AF':
    #           domain.append(('categ_id.activo_fijo', '=', True))
    #       elif tipo_sr == 'S':
    #           domain.append(('type', '=', 'service'))
    #       elif tipo_sr == 'I':
    #           domain.append(('categ_id.activo_fijo', '!=', True))
    #           domain.append(('type', '!=', 'service'))
    #       record.product_validos_ids = self.env['product.product'].search(domain).ids

    @api.multi
    @api.depends('name')
    def get_attachments_docs(self):
        pool_po = self.env['purchase.order']
        pool_invoice = self.env['account.invoice']
        pool_voucher = self.env['account.voucher']
        pool_adj = self.env['grp.cotizaciones']
        pool_apg = self.env['grp.compras.apg']
        pool_sc = self.env['grp.solicitud.compra']
        pool_lpc = self.env['grp.linea.pedido.compra']
        for sr in self:
            domain = False
            sc_ids = pool_sc.suspend_security().search([('solicitud_recursos_doc', '=', sr.name)])
            lpc_ids = pool_lpc.suspend_security().search([('solicitud_compra_id', 'in', sc_ids.ids)])
            pc_ids = []
            for line_pc in lpc_ids:
                pc_ids.append(line_pc.pedido_compra_id.id)
            pc_ids = list(set(pc_ids))
            po_ids = pool_po.suspend_security().search([('pedido_compra_id', 'in', pc_ids), ('state', 'not in', ['cancel'])])
            inv_ids = pool_invoice.suspend_security().search([('orden_compra_id', 'in', po_ids.ids),
                                                    ('state', 'not in', ['cancel', 'cancel_siif', 'cancel_sice'])])
            apg_ids = pool_apg.suspend_security().search([('pc_id', 'in', pc_ids), ('state', 'not in', ['anulada'])])
            av_ids = pool_voucher.suspend_security().search([('invoice_id', 'in', inv_ids.ids),('state', 'not in', ['cancel'])])
            adj_ids = pool_adj.suspend_security().search([('pedido_compra_id', 'in', pc_ids), ('state', 'not in', ['cancelado'])])
            if len(sc_ids):
                domain = ['|','|','|','|','|','|', '|', '&', ('res_id', '=', sr.id), ('res_model', '=', 'grp.compras.solicitud.recursos.almacen'),
                          '&', ('res_id', 'in', pc_ids), ('res_model', '=', 'grp.pedido.compra'),
                          '&', ('res_id', 'in', sc_ids.ids), ('res_model', '=', 'grp.solicitud.compra'),
                          '&', ('res_id', 'in', po_ids.ids), ('res_model', '=', 'purchase.order'),
                          '&', ('res_id', 'in', inv_ids.ids), ('res_model', '=', 'account.invoice'),
                          '&', ('res_id', 'in', av_ids.ids), ('res_model', '=', 'account.voucher'),
                          '&', ('res_id', 'in', adj_ids.ids), ('res_model', '=', 'grp.cotizaciones'),
                          '&', ('res_id', 'in', apg_ids.ids), ('res_model', '=', 'grp.compras.apg'),
                          ]

            if not domain:
                domain = [('res_id', '=', sr.id), ('res_model', '=', 'grp.compras.solicitud.recursos.almacen')]
            docs = self.env['ir.attachment'].search(domain)
            sr.attachment_ids = docs.ids

    @api.depends('tipo_sr','state')
    def _compute_lineas_readonly(self):
        for record in self:
            if record.state in ['rechazado','aprobado','esperando_almacen']:
                record.lineas_readonly = True
            elif record.state == 'inicio':
                record.lineas_readonly = False
            elif record.state in ['codificando']:
                if self.env.user.has_group('grp_seguridad.grp_compras_sr_Encargado_de_almacen'):
                    record.lineas_readonly = False
                else:
                    record.lineas_readonly = True
            elif record.state == 'en_aprobacion':
                if record.tipo_sr == 'PL':
                    if self.env.user.has_group('grp_compras_estatales.grp_sr_aprobador_planif'):
                        record.lineas_readonly = False
                    else:
                        record.lineas_readonly = True
                else:
                    if self.env.user.has_group('grp_seguridad.grp_compras_sr_Aprobador'):
                        record.lineas_readonly = False
                    else:
                        record.lineas_readonly = True
                record.lineas_readonly = False
            else:
                record.lineas_readonly = False

    @api.model
    def create(self, vals):
        self_obj = super(grp_solicitud_recursos_v8, self).create(vals)
        if self_obj.tipo_sr in ['PL']:
            solicitante_pl = self.env['res.users'].has_group('grp_compras_estatales.grp_sr_solicitante_planif')
            aprobador_pl = self.env['res.users'].has_group('grp_compras_estatales.grp_sr_aprobador_planif')
            if not solicitante_pl and not aprobador_pl:
                raise exceptions.ValidationError(u'No puede crear una SR de tipo planificada')
        return self_obj

    @api.multi
    def write(self, vals):
        super(grp_solicitud_recursos_v8, self).write(vals)
        for rec in self:
            if rec.tipo_sr in ['PL']:
                solicitante_pl = self.env['res.users'].has_group('grp_compras_estatales.grp_sr_solicitante_planif')
                aprobador_pl = self.env['res.users'].has_group('grp_compras_estatales.grp_sr_aprobador_planif')
                if not solicitante_pl and not aprobador_pl:
                    raise exceptions.ValidationError(u'No puede editar una SR de tipo planificada')
        return True


    @api.model
    def _update_analytic_entries(self, limit=5000, sr_ids=[]):
        # Proceso de actualización de dimensiones y creación de apuntes analíticos.
        logging.info('Ejecutando Cron de actualización de dimensiones y creación de apuntes analíticos')
        ICP = self.env['ir.config_parameter']
        domain = [('grp_sr_id','!=',False)]
        last_sr_id = ICP.get_param('last_updated_sr_id')
        if sr_ids:
            domain.append(('id','in',sr_ids))
        elif last_sr_id:
            domain.append(('id','>',last_sr_id))

        records2update = self.search(domain, limit=limit, order="id")
        logging.info('Cantidad de records a actualizar: ' + str(len(records2update)))

        AccountAnalyticPlan = self.env['account.analytic.plan.instance']
        StockPicking = self.env['stock.picking']
        AccountMove = self.env['account.move']
        StockLocation = self.env['stock.location']
        StockQuant = self.env['stock.quant']
        cr = self.env.cr

        def _get_debit_credit_account_id(move):
            location_from = move.location_id
            location_to = move.quant_ids and move.quant_ids[0].location_id or False
            company_from = StockLocation._location_owner(location_from)
            company_to = StockLocation._location_owner(location_to)
            credit_account_id = False
            debit_account_id = False
            if company_to and (move.location_id.usage not in ('internal', 'transit') and move.location_dest_id.usage == 'internal' or company_from != company_to):
                try:
                    journal_id, acc_src, acc_dest, acc_valuation = StockQuant.with_context(force_company=company_to.id)._get_accounting_data_for_valuation(move)
                except:
                    return False, False
                if location_from and location_from.usage == 'customer':
                    credit_account_id = acc_dest
                    debit_account_id = acc_valuation
                else:
                    credit_account_id = acc_src
                    debit_account_id = acc_valuation
            if company_from and (move.location_id.usage == 'internal' and move.location_dest_id.usage not in ('internal', 'transit') or company_from != company_to):
                try:
                    journal_id, acc_src, acc_dest, acc_valuation = StockQuant.with_context(force_company=company_from.id)._get_accounting_data_for_valuation(move)
                except:
                    return False, False
                if location_to and location_to.usage == 'supplier':
                    credit_account_id = acc_valuation
                    debit_account_id = acc_src
                else:
                    credit_account_id = acc_valuation
                    debit_account_id = acc_dest
            return credit_account_id, debit_account_id

        for record in records2update:
            logging.info('Analizando SR ID %s Nro Interno %s' % (record.id, record.name))
            # 1. Actualizar dimensiones de la SR
            # 2. Buscar si tiene stock.picking asociado y actualizar dimensiones
            acc_moves = AccountMove.browse()
            pickings = StockPicking.search(['|',('doc_origin','=',record.id),('origin','=',record.name)])
            for line in record.grp_sr_id:
                ##if record.tipo_sr in ('I','AF'):
                if not line.analytics_id:
                    account_ids = []
                    account_ids.append((0, 0, {
                        'account_id': line.account_id.id,
                        'hr_department_id': record.department_id.id,
                        'hr_department_id_not_apply': False,
                        'analytic_account_id_not_apply': True,
                        'dim_multi_id_not_apply': True,
                    }))
                    analytics_id = AccountAnalyticPlan.create({ 'account_ids': account_ids }).id
                    cr.execute('UPDATE grp_compras_solicitud_recursos_line_sr SET analytics_id=%s WHERE id=%s', (analytics_id, line.id))
                    line.invalidate_cache()
                    logging.info('Se creo analytic plan ID %s asociado al SR line ID %s' % (analytics_id, line.id))
                else:
                    analytics_id = line.analytics_id.id
                for picking in pickings:
                    logging.info('picking ID %s' % (picking.id))
                    for stock_move in picking.move_lines:
                        if stock_move.product_id.id == line.product_id.id:
                            logging.info('stock move ID %s' % (stock_move.id))
                            credit_account_id, debit_account_id = _get_debit_credit_account_id(stock_move)
                            logging.info('credit_account_id %s' % (credit_account_id))
                            logging.info('debit_account_id %s' % (debit_account_id))

                            cr.execute('UPDATE stock_move SET analytics_id=%s WHERE id=%s', (analytics_id, stock_move.id))
                            stock_move.invalidate_cache()
                            logging.info('Se asocio analytic plan ID %s asociado al stock_move ID %s' % (analytics_id, stock_move.id))
                            break
                    # 3. Buscar account.move asociado al picking por referencia
                    moves = AccountMove.search([('ref','=',picking.name)])
                    for move in moves:
                        logging.info('account move ID %s' % (move.id))
                        acc_ids = list(set([ l.account_id.id for l in move.line_id ]))
                        for move_line in move.line_id:
                            logging.info('move_line ID %s move_line.account_id %s' % (move_line.id, move_line.account_id.id))
                            logging.info('debe %s' % (move_line.debit))
                            logging.info('haber %s' % (move_line.credit))

                            if move_line.account_id.id == debit_account_id \
                               or move_line.debit > 0 \
                               or (len(acc_ids)==2 and credit_account_id in acc_ids and move_line.account_id.id != credit_account_id): # Actualizar apunte de la cuenta que va al débito al crear asiento de la transferencia
                                cr.execute('UPDATE account_move_line SET analytics_id=%s WHERE id=%s', (analytics_id, move_line.id))
                                move_line.invalidate_cache()
                                # 4 Para los account.move.line que se le agregó dimensiones crear apuntes analíticos si el move está asentado
                                if move.state == 'posted':
                                    try:
                                        if move_line.analytic_lines:
                                            move_line.analytic_lines.unlink()
                                        move_line.create_analytic_lines()
                                        logging.info('Se crearon apuntes analiticos para el move_line ID %s del move ID %s' % (move_line.id, move.id))
                                    except Exception as e:
                                        logging.info('Exception al intentar crear apuntes analiticos')
                                        logging.info(e)
                                else:
                                    logging.info('Asiento no validado')

                                if move.id not in acc_moves.ids:
                                    acc_moves |= move
                                break
                cr.commit()

            ICP.set_param('last_updated_sr_id', record.id)
            cr.commit()

        logging.info('Finaliza Cron de actualización de dimensiones y creación de apuntes analíticos')


class grp_compras_solicitud_recursos_line_sr_v8(models.Model):
    _inherit = 'grp.compras.solicitud.recursos.line.sr'

    @api.one
    @api.constrains('cantidad_solicitada')
    def _check_cantidad_entera(self):
        if not self.cantidad_solicitada:
            raise exceptions.ValidationError('La cantidad solicitada no puede ser 0')
        if self.uom_id:
            if self.uom_id.rounding == 1.0 and\
                    self.cantidad_solicitada and\
                    not self.cantidad_solicitada.is_integer():
                raise exceptions.ValidationError('La cantidad solicitada debe ser entera')
        if self.cantidad_solicitada and self.cantidad_solicitada < 0:
            raise exceptions.ValidationError('La cantidad solicitada debe ser positiva')

    @api.multi
    @api.depends('product_id')
    def _compute_udm_domain_ids(self):
        uom_obj = self.env['product.uom']
        for record in self:
            if record.product_id:
                prod_uom_id = record.product_id.product_tmpl_id.uom_id or record.product_id.uom_id
                uom_ids = [prod_uom_id]
                if record.product_id.grp_sice_cod:
                    pool_art_serv_obra = self.env['grp.sice_art_serv_obra']
                    pool_uom = self.env['product.uom']
                    sice_cod = record.product_id.grp_sice_cod
                    art_id = pool_art_serv_obra.search([('cod', '=', sice_cod)])
                    if len(art_id) > 0:
                        art_id = art_id[0]
                    for uom in art_id.unidades_med_ids:
                        prod_uom = pool_uom.search([('sice_uom_id', '=', uom.id)])
                        if len(prod_uom) > 0:
                            prod_uom = prod_uom[0]
                        if prod_uom and prod_uom.category_id.id == record.product_id.product_tmpl_id.uom_id.category_id.id:
                            uom_ids.append(prod_uom)
                ids = [uom.id for uom in uom_ids]
            else:
                ids = uom_obj.search([]).ids
            record.udm_domain_ids = ids

    udm_domain_ids = fields.Many2many('product.uom', string='Dominio Udm', compute='_compute_udm_domain_ids')
    tipo_sr = fields.Selection(string='Tipo SR', related="grp_id.tipo_sr", readonly=True)
    sr_warehouse = fields.Many2one(string=u'Almacén', related="grp_id.warehouse", readonly=True)
    parent_state = fields.Selection(string='Estado Solicitud', related="grp_id.state", readonly=True, store=True) # backward compatibility
    sr_pedidos_count = fields.Integer(string='Cantidad Pedidos de la SR', compute="_sr_pedidos_count", search='_search_sr_pedidos_count')

    @api.one
    def _sr_pedidos_count(self):
        scs = self.env['grp.solicitud.compra'].search([('solicitud_recursos_id', '=', self.grp_id.id)])
        line_pcs = self.env['grp.linea.pedido.compra'].search([('solicitud_compra_id', 'in', scs.ids)])
        pedido_ids = set(line.pedido_compra_id.id for line in line_pcs)
        self.sr_pedidos_count = len(pedido_ids)

    def _search_sr_pedidos_count(self, operator, value):
        _sql = """  SELECT sra.id
                    FROM grp_compras_solicitud_recursos_almacen sra
                        left join grp_solicitud_compra sc ON (sc.solicitud_recursos_id=sra.id)
                        left join grp_linea_pedido_compra lpc ON (lpc.solicitud_compra_id=sc.id)
                    GROUP BY sra.id
                    HAVING COUNT(DISTINCT lpc.pedido_compra_id) %s %%s """ % (operator)
        self._cr.execute(_sql, (value or 0,))
        sra_ids = [ x[0] for x in self._cr.fetchall() ]
        self._cr.execute("SELECT sr_id FROM grp_compras_solicitud_recursos_almacen WHERE id in %s", (tuple(sra_ids or [-1]),))
        sr_ids = [ x[0] for x in self._cr.fetchall() ]
        return [('grp_id', 'in', sr_ids)]

class grp_compras_solicitud_recursos_line_sr_af_v8(models.Model):
    _inherit = 'grp.compras.solicitud.recursos.line.sr.af'

    @api.depends('grp_id','product_id')
    def _get_domain_account_asset_asset(self):
        quant_pool = self.env['stock.quant']
        for rec in self:
            list_assets = []
            if rec.product_id:
                assets = self.env['account.asset.asset'].search([('product_id', '=', rec.product_id.id),('state','in',['open','close'])])
                for asset in assets:
                    # if asset.user_id and asset.user_id.id != self.env.user.id:
                    #     continue

                    quants = quant_pool.search([('product_id', '=', asset.product_id.id)])
                    for qt in quants:
                        if asset.id in list_assets:
                            continue
                        if qt.location_id.usage not in ['internal']:
                            continue
                        self._cr.execute("""
                        select location_id as location_id
                        from stock_quant
                        where product_id = %s
                        group by location_id
                        having sum(qty) > 0""", [asset.product_id.id])
                        res = self._cr.dictfetchall()
                        loc_ids = [r['location_id'] for r in res]
                        if qt.location_id.id not in loc_ids:
                            continue
                        #wh = self.env['stock.location'].get_warehouse(qt.location_id)
                        #wh_obj = self.env['stock.warehouse'].browse(wh)
                        #if wh_obj.encargado_ids and self.env.user.id not in wh_obj.encargado_ids.ids:
                        #    continue
                        list_assets.append(asset.id)

            if rec.articulo_af and rec.articulo_af.id not in list_assets:
                rec.articulo_af = False
            rec.domain_account_asset_asset = list_assets

    domain_account_asset_asset = fields.Many2many(
        string=u'Domain activos permitidos',
        comodel_name=u'account.asset.asset',
        compute='_get_domain_account_asset_asset'
    )
    restrict_lot_id = fields.Many2one('stock.production.lot', 'Lote', )

    @api.one
    @api.constrains('articulo_af','grp_id')
    def _check_af_unicity(self):
        if self.grp_id and self.articulo_af and \
           self.search_count([('id','!=',self.id),('grp_id','=',self.grp_id.id),('articulo_af','=',self.articulo_af.id)]):
            raise exceptions.ValidationError(u'No puede seleccionar el mismo artículo de AF en más de una línea.')

class Product(models.Model):
    _inherit = 'product.product'

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        if self._context.get('from_sr', False) and \
           self._context.get('tipo_sr', False):
            tipo_sr = self._context.get('tipo_sr')
            domain = [('purchase_ok','=',True)]
            if tipo_sr == 'AF':
                domain.append(('categ_id.activo_fijo', '=', True))
            elif tipo_sr == 'S':
                domain.append(('type', '=', 'service'))
            elif tipo_sr == 'I':
                domain.append(('categ_id.activo_fijo', '!=', True))
                domain.append(('type', '!=', 'service'))
            if not args:
                args = []
            args = domain + args
        return super(Product, self)._search(args, offset=offset, limit=limit, order=order, count=count, access_rights_uid=access_rights_uid)
