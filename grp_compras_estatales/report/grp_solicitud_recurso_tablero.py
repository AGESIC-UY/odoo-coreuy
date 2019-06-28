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
from openerp import models, fields, api, exceptions, _
from openerp import tools

class GrpSolicitudRecurso(models.Model):
    _name = 'grp.solicitud.recurso.tablero'
    _auto = False
    _description = u'Solcitud recurso'

    name = fields.Char('Solicitud Recurso')
    date_start = fields.Date('Fecha de Solicitud')
    tipo_sr = fields.Selection([('I', 'Insumos/Materiales'),
                            ('S', 'Servicios'),
                            ('AF', 'Activo Fijo'),
                            ('PL', 'Planificada')], u'Tipo SR')
    ubicacion = fields.Many2one('stock.location', string =u'Ubicación')
    operating_unit_id = fields.Many2one('operating.unit', 'Unidad ejecutora')
    solicitante_id= fields.Many2one('res.users', string='Solicitante')
    aprobador_id = fields.Many2one('res.users', 'Aprobador')
    description = fields.Char(u'Observaciones')
    state = fields.Selection([
        ('inicio', 'Borrador'),
        ('en_aprobacion', u'En aprobación'),
        ('rechazado', 'Rechazado'),
        ('codificando', u'Aprobado'),
        ('esperando_almacen', u'En Proceso'),
        ('aprobado', 'Cerrado'),],'Estado')

    estado_en_proc = fields.Selection([('eprocalm', u'En proceso almacén'),
                                      ('eaprobcomp', u'En Aprobación Compras'),
                                      ('envcomp', u'Enviado a Depto de compras'),
                                      ('pendrecep', u'Pendiente Recepción'),
                                     ], "Estado en proceso")

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'grp_solicitud_recurso_tablero')
        cr.execute("""
            CREATE OR replace VIEW grp_solicitud_recurso_tablero AS (
                SELECT 
	sol_rec.id,
	soc_rec_base.name,
	sol_rec.ubicacion,
	sol_rec.operating_unit_id,
	sol_rec.description,
	soc_rec_base.date_start,
	soc_rec_base.tipo_sr,
	soc_rec_base.solicitante_id,
	soc_rec_base.aprobador_id,
	soc_rec_base.state,
	sol_rec.estado_en_proc
FROM 
	grp_compras_solicitud_recursos_almacen AS sol_rec,
	grp_compras_solicitud_recursos AS soc_rec_base -- DELEGATION PARENT CLASS
WHERE
	sol_rec.sr_id = soc_rec_base.id AND
	sol_rec.id IN (SELECT
	DISTINCT(sol_compra.solicitud_recursos_id)
FROM 
	grp_solicitud_compra AS sol_compra,
	grp_pedido_compra AS pedido_compra
WHERE
	sol_compra.pedido_compra_id = pedido_compra.id AND
	sol_compra.state = 'open' AND
	pedido_compra.state NOT IN ('cancelado_sice','cancelado'))
)
        """)
