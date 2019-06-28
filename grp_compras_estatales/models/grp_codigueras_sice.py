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


class sicec_doc_proveedor(osv.osv):
    """La clase sicec_doc_proveedor"""

    _name = 'sicec.doc.proveedor'
    _rec_name = 'descTipoDocProv'
    _columns = {
        'tipoDocProv': fields.char('Tipo', size=1),
        'descTipoDocProv': fields.char('Descripción', size=200),
        'proveedorRupe': fields.char('RUPE', size=1),
        'propioTesoreria': fields.char('Tesorería', size=1),
        'formato': fields.char('Formato', size=200),
        'pcpd': fields.char('PCPD', size=1),
    }


sicec_doc_proveedor()


class sicec_estado_compra(osv.osv):
    """La clase sicec_estado_compra"""

    _name = 'sicec.estado.compra'
    _rec_name = 'descEstado'
    _columns = {
        'codEstado': fields.integer('Código'),
        'descEstado': fields.char('Descripción', size=200),
    }


sicec_estado_compra()


class sicec_inciso(osv.osv):
    """La clase sicec_inciso"""

    _name = 'sicec.inciso'
    _rec_name = 'descInciso'
    _columns = {
        'idInciso': fields.integer('Código'),
        'descInciso': fields.char('Descripción', size=200),
    }


sicec_inciso()


class sicec_moneda(osv.osv):
    """La clase sicec_moneda"""

    _name = 'sicec.moneda'
    _rec_name = 'descMoneda'
    _columns = {
        'codMoneda': fields.integer('Código'),
        'descMoneda': fields.char('Descripción', size=200),
        'currency_id': fields.many2one('res.currency', 'Moneda GRP'),
    }


sicec_moneda()


class sicec_subtipo_compra(osv.osv):
    """La clase sicec_subtipo_compra"""

    _name = 'sicec.subtipo.compra'
    _rec_name = 'descSubtipoCompra'
    _columns = {
        'idTipoCompra': fields.many2one('sicec.tipo.compra', 'Tipo compra', required=True),
        'idSubtipoCompra': fields.char('Subtipo', size=10),
        'descSubtipoCompra': fields.char('Descripción', size=200),
        'comprasCentralizadas': fields.char('Centralizada', size=20),
        'fondosRotatorios': fields.char('Fondo rotatorio', size=1),
        'publicacionLlamado': fields.char('Llamado', size=1),
        'condPrecioOfertas': fields.char('Condición oferta', size=10),
        'validaRupe': fields.char('RUPE', size=1),
        'active': fields.boolean('Activo')
    }
    _defaults = {
        'active': True
    }


sicec_subtipo_compra()


class sicec_tipo_compra(osv.osv):
    """La clase sicec_tipo_compra"""

    _name = 'sicec.tipo.compra'
    _rec_name = 'descTipoCompra'
    _columns = {
        'idTipoCompra': fields.char('Tipo', size=2),
        'descTipoCompra': fields.char('Descripción', size=200),
        'interrelacionSIIF': fields.char('SIIF', size=1),
        'comprasCentralizadas': fields.char('Centralizada', size=20),
        'ofertaEconomica': fields.char('Oferta', size=1),
        'plazoMinOferta': fields.integer('Plazo'),
        'actoApertura': fields.char('Apertura', size=1),
        'resolucionObligatoria': fields.char('Resolución', size=1),
        'solicitudesLlamado': fields.char('Llamado', size=1),
        'ampliaciones': fields.char('Ampliaciones', size=1),
        'topeLegal': fields.char('Tope', size=1),
        'pcpd': fields.char('PCPD', size=1),
        'urgente': fields.boolean('Urgente'),
        'active': fields.boolean('Activo')
    }
    _defaults = {
        'active': True,
        'urgente': False
    }


sicec_tipo_compra()


class sicec_uc(osv.osv):
    """La clase sicec_uc"""

    # Ahora este es el codigo
    _name = 'sicec.uc'
    # _rec_name = 'descUC'

    def _get_uc_name(self, cr, uid, ids, name, args, context=None):
        res = {}
        for uc in self.browse(cr, 1, ids, context=context):
            res[uc.id] = (uc.descUC or '') + ' - ' + (uc.idUE.descUE or '')
        return res

    _columns = {
        'idInciso': fields.many2one('sicec.inciso', 'Inciso', required=True),
        'idUE': fields.many2one('sicec.ue', 'UE', required=True),
        'idUC': fields.integer('Código'),
        'descUC': fields.char('Descripción', size=200),
        'interrelacionSIIF': fields.char('SIIF', size=1),
        'name': fields.function(_get_uc_name, type="char", string="Nombre"),
    }


sicec_uc()


class sicec_ue(osv.osv):
    """La clase sicec_ue"""

    _name = 'sicec.ue'
    _rec_name = 'descUE'
    _columns = {
        'idInciso': fields.many2one('sicec.inciso', 'Inciso', required=True),
        'idUE': fields.integer('Código'),
        'descUE': fields.char('Descripción', size=200),
    }

sicec_ue()


class product_uom(osv.osv):
    _inherit = 'product.uom'

    _columns = {
        'sice_uom_id': fields.many2one('grp.sice_unidades_med', string=u'UdM SICE'),
        'cod_udm': fields.related('sice_uom_id', 'cod', string=u'Código UdM SICE', type='integer'),
    }

    def onchange_sice_uom(self, cr, uid, ids, sice_uom_id, context=None):
        result = {}
        result.setdefault('value', {})
        result['value'] = {'cod_udm': False}

        if sice_uom_id:
            sice_uom = self.pool.get('grp.sice_unidades_med').browse(cr, uid, sice_uom_id, context=context)
            result['value'].update({'cod_udm': sice_uom.cod})

        return result


product_uom()
