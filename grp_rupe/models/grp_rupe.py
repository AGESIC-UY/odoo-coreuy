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

import datetime
import logging
from dateutil import parser
from openerp.osv import osv, fields, expression

class rupe_cuentas_bancarias(osv.osv):
    """La clase rupe_cuentas_bancarias"""

    _name = 'rupe.cuentas.bancarias'

    _columns = {
        'cnt_id': fields.integer('Cuenta'),
        'cnt_ciudad_banco': fields.char('Ciudad Pagador', size=255),
        'cnt_ciudad_banco_intermediario': fields.char('Ciudad Intermediario', size=255),
        'cnt_codigo_swift': fields.char('SWIFT Pagador', size=255),
        'cnt_codigo_swift_banco_intermedio': fields.char('SWIFT Intermediario', size=255),
        'cnt_crea_fecha': fields.datetime('Fecha alta'),
        'cnt_descripcion': fields.char('Descripción', size=255),
        'cnt_direccion_banco_destino': fields.char('Dirección destino', size=255),
        'cnt_estado_datos_descripcion': fields.char('Descripción estado de la cuenta', size=255),
        'cnt_nombre_banco': fields.char('Nombre Pagador', size=255),
        'cnt_nombre_banco_intermedio': fields.char('Nombre Intermediario', size=255),
        'cnt_nro_cuenta': fields.char('Número de cuenta', size=255),
        'cnt_numero_aba': fields.char('Nombre ABA o Routing', size=255),
        'cnt_sucursal': fields.char('Descripción sucursal', size=255),
        'cnt_titular_cuenta': fields.char('Titular de la cuenta', size=255),
        'cnt_ultmod_fecha': fields.datetime('Fecha modificación'),
        'cnt_version': fields.integer('Versión'),
        'codigo_banco': fields.char('Código del Banco según BCU', size=7),
        'cnt_estado_datos': fields.integer('Estado de la cuenta'),
        'codigo_pais': fields.char('Código país residente', size=3),
        'codigo_pais_int': fields.char('Código país Intermediario', size=3),
        'cnt_proveedor_prv_id': fields.integer('Proveedor'),
        'codigo_sucursal': fields.char('Sucursal', size=7),
        'nombre_sucursal': fields.char('Nombre Sucursal', size=255),
        'codigo_tipo_cuenta': fields.char('Tipo de cuenta', size=2),
        'codigo_moneda': fields.char('Moneda', size=3),
        'cnt_iban': fields.char('IBAN', size=255),
        'active': fields.boolean('Activo'),
        'modificado': fields.boolean('Modificado'),
        'ultima_modificacion': fields.datetime(u'Última modificación'),

        'brou_cnt_nro_cuenta_viejo': fields.char('Número de cuenta viejo', size=255),
        'brou_nombre_sucursal_viejo': fields.char('Nombre Sucursal viejo', size=255),
        'brou_codigo_sucursal_viejo': fields.char('Sucursal viejo', size=7),

    #     brou_cnt_nro_cuenta_viejo ,brou_codigo_sucursal_viejo ,brou_nombre_sucursal_viejo
    }
    _defaults = {
        'active': True,
        'modificado': False,
    }


    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        reads = self.read(cr, uid, ids, ['cnt_nombre_banco', 'codigo_sucursal', 'cnt_nro_cuenta', 'nombre_sucursal'],
                          context=context)
        res = []
        for record in reads:
            res.append((record['id'], ('%s-%s-%s-%s') % (
                record['cnt_nombre_banco'], record['codigo_sucursal'], record['cnt_nro_cuenta'],
                record['nombre_sucursal'])))
        return res


    # buscar datos de cuenta
    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if operator in expression.NEGATIVE_TERM_OPERATORS:
            domain = [('cnt_nombre_banco', operator, name), ('cnt_nombre_banco', operator, name)]
        else:
            domain = ['|', '|', '|', ('cnt_nombre_banco', operator, name), ('codigo_sucursal', operator, name),
                      ('cnt_nro_cuenta', operator, name), ('nombre_sucursal', operator, name)]
        ids = self.search(cr, user, expression.AND([domain, args]), limit=limit, context=context)
        return self.name_get(cr, user, ids, context=context)

rupe_cuentas_bancarias()


class rupe_datos_comunicacion_proveedor(osv.osv):
    """La clase rupe_datos_comunicacion_proveedor"""

    _name = 'rupe.datos.comunicacion.proveedor'
    _columns = {
        'dco_id': fields.integer('Código comunicación'),
        'dco_comentario': fields.char('Comentario', size=255),
        'dco_crea_fecha': fields.datetime('Fecha alta'),
        'dco_destino': fields.char('Valor comunicación', size=255),
        'dco_ultmod_fecha': fields.datetime('Fecha modificación'),
        'dco_version': fields.integer('Versión'),
        'dco_proveedor_prv_id': fields.integer('Proveedor'),
        'codigo_tipo_comunic': fields.char('Tipo comunicación', size=7),
        'active': fields.boolean('Activo'),
        'modificado': fields.boolean('Modificado'),
        'ultima_modificacion': fields.datetime(u'Última modificación'),
    }
    _defaults = {
        'active': True,
        'modificado': False,
    }
rupe_datos_comunicacion_proveedor()


class rupe_proveedores(osv.osv):
    """La clase rupe_proveedores"""

    _name = 'rupe.proveedores'
    _columns = {
        'prv_id': fields.integer('Proveedor'),
        'prv_cod_fiscal': fields.char('Código fiscal (RUT)', size=255),
        'prv_correo_electronico': fields.char('Correo electrónico', size=255),
        'prv_crea_fecha': fields.datetime('Fecha alta'),
        'prv_denominacion_social': fields.char('Denominación Social', size=255),
        'prv_descripcion_respresentantes': fields.char('Descripción de los representantes', size=2000),
        'prv_domicilio_fiscal': fields.char('Domicilio fiscal', size=255),
        'codigo_depto_fiscal': fields.char('Departamento', size=4),
        'prv_loc_fiscal_nombre': fields.char('Localidad', size=255),
        'prv_nombre_fantasia': fields.char('Nombre fantasía', size=255),
        'prv_sitio_web': fields.char('Sitio web', size=255),
        'prv_ultmod_fecha': fields.datetime('Fecha modificación'),
        'prv_version': fields.integer('Versión'),
        'dom_codigo_pais': fields.char('DN: País', size=3),
        'dom_codigo_depto': fields.char('DN: Departamento', size=5),
        'dom_depto_exterior': fields.char('DN: Departamento país extranjero', size=100),
        'dom_codigo_local': fields.char('DN: Localidad', size=3),
        'dom_ciudad_exterior': fields.char('DN: Ciudad país extranjero', size=100),
        'dom_codigo_tipo_vial': fields.char('DN: Tipo de vialidad', size=3),
        'dom_nombre_vialidad': fields.char('DN: Nombre de la vialidad', size=255),
        'dom_nro_puerta': fields.char('DN: Nro. de puerta', size=255),
        'dom_bis': fields.char('DN: Bis', size=1),
        'dom_apto': fields.char('DN: Nro. de apartamento', size=10),
        'dom_codigo_postal': fields.char('DN: Código postal', size=255),
        'dom_descripcion': fields.char('DN: Información adicional', size=255),
        'dom_ruta': fields.char('DN: Ruta', size=255),
        'dom_kilometro': fields.char('DN: Kilómetro', size=255),
        'dom_manzana_catastral': fields.char('DN: Manzana Catastral', size=255),
        'dom_solar_catastral': fields.char('DN: Solar Catastral', size=255),
        'dom_desc_tipo_ent_col': fields.char('DN: Tipo de entrada colectiva', size=255),
        'dom_nombre_inmueble': fields.char('DN: Nombre del inmueble', size=255),
        'dom_codigo_par': fields.char('DN: Código de paridad', size=5),
        'dom_crea_fecha': fields.datetime('DN: Fecha alta'),
        'dom_ultmod_fecha': fields.datetime('DN: Fecha modificación'),
        'codigo_estado': fields.char('Estado del proveedor', size=6, select=1),
        'codigo_nat_juridica': fields.char('Naturaleza Jurídica', size=2),
        'codigo_pais': fields.char('País', size=3),
        'codigo_tipo_documento': fields.char('Tipo de documento', size=3),
        'active': fields.boolean('Activo'),
        'modificado': fields.boolean('Modificado'),
        'ultima_modificacion': fields.datetime(u'Última modificación'),
        'search_id': fields.many2one('grp.proveedores.rupe.busqueda', 'Busqueda'),
        'incluido': fields.boolean('Incluido'),
    }

    _defaults = {
        'active': True,
        'modificado': False,
        'incluido': False,
    }

    def set_attrib(self, cr, uid, ids, context=None):
        # Mapeo de los datos del Proveedor
        partner_obj = self.pool.get("res.partner")
        for object in self.browse(cr, uid, ids):
            tipo_doc = 'R'
            if object.codigo_tipo_documento.strip() == 'RUT':
                tipo_doc = 'R'
            if object.codigo_tipo_documento.strip() == 'CI':
                tipo_doc = 'CI'
            if object.codigo_tipo_documento.strip() == 'PS':
                tipo_doc = 'PS'
            if object.codigo_tipo_documento.strip() == 'NIE':
                tipo_doc = 'NIE'
            if object.codigo_tipo_documento.strip() == 'CFE':
                tipo_doc = 'CFE'

            partner_ids = partner_obj.search(cr, uid, [('nro_doc_rupe','!=',False),('nro_doc_rupe','=',object.prv_cod_fiscal)], context=context)
            if partner_ids:
                vals = {
                    'name':object.prv_denominacion_social,
                    'street': object.prv_domicilio_fiscal,
                    'city': object.prv_loc_fiscal_nombre,
                    'email': object.prv_correo_electronico,
                    'id_rupe': object.prv_id,
                    'fecha_creacion_rupe': object.prv_crea_fecha,
                    'version_rupe': object.prv_version,
                    'estado_rupe': object.codigo_estado,
                    'tipo_doc_rupe': tipo_doc,
                    'nro_doc_rupe': object.prv_cod_fiscal,
                    'is_company': True,
                    'supplier': True,
                    'fecha_modif_rupe': datetime.datetime.now().strftime("%Y-%m-%d"),
                }
                partner_obj.write(cr, uid, partner_ids, vals, context=context)
                self.write(cr, uid, [object.id], {'incluido': True})

            else:
                # Valores por defecto a traves del 'context'
                context['default_name'] = object.prv_denominacion_social
                context['default_referencia_proveedor'] = object.prv_nombre_fantasia
                context['default_street'] = object.prv_domicilio_fiscal
                context['default_city'] = object.prv_loc_fiscal_nombre
                context['default_email'] = object.prv_correo_electronico
                context['default_id_rupe'] = object.prv_id
                context['default_fecha_creacion_rupe'] = object.prv_crea_fecha
                context['default_version_rupe'] = object.prv_version
                context['default_estado_rupe'] = object.codigo_estado
                context['default_tipo_doc_rupe'] = tipo_doc

                context['default_nro_doc_rupe'] = object.prv_cod_fiscal
                context['default_is_company'] = True
                context['hide_grp_buttons'] = False
                context['default_fecha_modif_rupe'] = datetime.datetime.now().strftime("%Y-%m-%d")

                context['default_customer'] = False
                context['default_supplier'] = True

                context['desde_crear_prv_grp'] = True
                context['id_staging'] = object.id

                return {
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'res.partner',
                    'target': 'new',
                    'context': context,
                }


rupe_proveedores()


class rupe_historico_novedades(osv.osv):
    _name = 'rupe.historico.novedades'
    _order = 'id desc'
    _columns = {
        'name': fields.char('Tipo de novedad', size=50),
        'operacion': fields.char(u'Operación', size=1),
        'objeto_id_rupe': fields.integer('Id RUPE'),
		'objeto_id_rupe_str': fields.char('Id RUPE', size=8),
        'descripcion': fields.char(u'Descripción', size=100),
        'prv_id': fields.integer('Id RUPE Proveedor'),
		'prv_id_str': fields.char('Id RUPE Proveedor', size=8),
        'fecha_modificacion': fields.datetime('Fecha RUPE'),
        'fecha_proceso': fields.datetime('Fecha de proceso'),
		'version': fields.char(u'Versión', size=4),
    }
    _defaults = {
        'fecha_proceso':fields.datetime.now,
    }
rupe_historico_novedades()

class rupe_novedades_error_log(osv.osv):
    _name = 'rupe.novedades.error.log'
    _order = 'id desc'
    _columns = {
        'name': fields.date('Fecha'),
        'fecha': fields.datetime('Fecha / Hora'),
        'funcion': fields.char(u'Función', size=50),
        'operacion': fields.char(u'Operación invocada', size=50),
        'msg_error_rupe': fields.char(u'Mensaje de error RUPE', size=500),
    }
    _defaults = {
        'name':fields.date.context_today,
        'fecha':fields.datetime.now,
    }
rupe_novedades_error_log()


class grp_proveedores_rupe_busqueda(osv.osv):
    _name = "grp.proveedores.rupe.busqueda"

    def default_description(self, cr, uid, context=None):
        """La descripción de la búsqueda"""
        hoy = datetime.datetime.now()
        return "Seleccionados el %s" % (str(hoy)[:16])

    _columns = {
        'name': fields.char(u'Descripción', size=200, required=True),
        'razon_social': fields.char(u'Razón Social'),
        'nombre_fantasia': fields.char(u'Nombre Fantasía'),
        'documento': fields.selection((('RUT', 'RUT'), ('CI', 'CI'), ('CFE', 'CFE'), ('PS', 'PS'), ('NIE', 'NIE')),
                                      'Documento'),
        'num_documento': fields.char(u'Número Documento'),
        'estado': fields.selection(
            (('ACTIVO', 'ACTIVO'), ('BAJA', 'BAJA'), ('ELIM', 'ELIM'), ('ENING', 'ENING'), ('CANC', 'CANC')), 'Estado'),
        'proveedores_ids': fields.one2many('rupe.proveedores', 'search_id', 'Proveedores'),
    }
    _defaults = {
        'name': default_description,
    }

    def grp_prove_buscar(self, cr, uid, ids, context=None):
        # Al disparar el boton de búsqueda se efectúa la consulta
        # Construir la consulta
        condicion = ""
        datos = {}
        for record in self.browse(cr, uid, ids):
            if record.razon_social:
                condicion += "prv_denominacion_social ilike %(razon_social)s"
                datos['razon_social'] = record.razon_social + "%"

            if record.nombre_fantasia:
                if condicion:
                    condicion += " and "
                condicion += "prv_nombre_fantasia ilike %(nombre_fantasia)s"
                datos['nombre_fantasia'] = record.nombre_fantasia + "%"

            if record.documento:
                if condicion: condicion += " and "
                condicion += "codigo_tipo_documento = %(documento)s"
                datos['documento'] = record.documento

            if record.num_documento:
                if condicion:
                    condicion += " and "
                condicion += "prv_cod_fiscal ilike %(num_documento)s"
                datos['num_documento'] = record.num_documento + "%"

            if record.estado:
                if condicion: condicion += " and "
                condicion += "codigo_estado = %(estado)s"
                datos['estado'] = record.estado


        # En caso de que no haya ningún valor ...
        if not condicion:
            #     condicion='1=1'
            raise osv.except_osv('Por favor', 'Ingrese al menos un criterio.')
            return False

        # La consulta
        consulta = "select id from rupe_proveedores where " + condicion
        #_logger.info('consulta: %s, datos: %s', consulta, datos)
        # Buscar
        cr.execute(consulta, datos)
        res = cr.fetchall()

        if cr.rowcount > 0:
            # Desvincular los proveedores que haya de una consulta anterior
            self.write(cr, uid, ids, {'proveedores_ids': [(5,)]}, context)

            # Grabar los nuevos vinculos con proveedores
            prov_list = []
            for prov in res:
                prov_list.append((4, prov[0]))
            self.write(cr, uid, ids, {'proveedores_ids': prov_list}, context)
        else:
            raise osv.except_osv('No hay resultados', 'Intente otros valores.')

        # Retornar True para actualizar la vista o False si no hay resultados
        return cr.rowcount

grp_proveedores_rupe_busqueda()


class grp_proveedores(osv.osv):
    _inherit = "res.partner"

    def crear_proveedor_grp(self, cr, uid, ids, context=None):
        for object in self.browse(cr, uid, ids):
            cr.execute("select id from rupe_proveedores where prv_id = %(prv_id)s", {'prv_id': object.id_rupe})
            if cr.rowcount > 0:
                res = cr.fetchone()
                self.pool.get('rupe.proveedores').write(cr, uid, [res[0]], {'incluido': True, }, context)
        return True

    def create(self, cr, uid, vals, context=None):

        pool_staging_rupe = self.pool.get('rupe.proveedores')

        source_crear_prov_grp = context.get('desde_crear_prv_grp',False)
        id_rupe_proveedores = context.get('id_staging',False)


        if source_crear_prov_grp:
            # Origen del create: funcionalidad "Crear Proveedor GRP"
            # _logger.info('VIENE de "Crear Proveedor GRP"')

            # Es requerido NRO_RUT y ID_RUPE
            if vals.get('nro_doc_rupe',False) and vals.get('id_rupe',False):
                 prv_rupe_ids = pool_staging_rupe.search(cr, uid, [('id','=',id_rupe_proveedores),
                                                                   ('prv_id','=',vals.get('id_rupe',False)),
                                                                   ('prv_cod_fiscal','=',vals.get('nro_doc_rupe',False)),
                                                                   ('incluido','=',False)], context=context)
                 # Llegado a este punto, la busqueda en la staging deberia encontrar un registro, pero podria no encontrarlo
                 # en caso de que el usuario haya cambiado manualmente en el form de res.partner el/o los dato/s correspondientes
                 # a Nro Documento y ID_RUPE.  ID del registro permanece incambiado ya que el usuario no lo puede editar
                 # Asi que si no encuentra registro, no se crea el proveedor
                 if not prv_rupe_ids:
                     raise osv.except_osv((u'Atención'), ('Imposible crear proveedor. No se pueden editar RUT y/o ID RUPE'))
            else:
                raise osv.except_osv((u'Atención'), ('Imposible crear proveedor. No existe RUT o ID RUPE'))

        elif vals.get('desde_import',False):
            if vals.get('nro_doc_rupe',False) and vals.get('id_rupe',False):
                 prv_rupe_ids = pool_staging_rupe.search(cr, uid, [('id','=',vals.get('id_staging',False)),
                                                                   ('prv_id','=',vals.get('id_rupe',False)),
                                                                   ('prv_cod_fiscal','=',vals.get('nro_doc_rupe',False)),
                                                                   ('incluido','=',False)], context=context)
                 # Llegado a este punto, la busqueda en la staging deberia encontrar un registro, pero podria no encontrarlo
                 # en caso de que el usuario haya cambiado manualmente en el form de res.partner el/o los dato/s correspondientes
                 # a Nro Documento y ID_RUPE.  ID del registro permanece incambiado ya que el usuario no lo puede editar
                 # Asi que si no encuentra registro, no se crea el proveedor
                 del vals['desde_import']
                 del vals['id_staging']
                 if not prv_rupe_ids:
                     raise osv.except_osv((u'Atención'), ('Imposible crear proveedor. No se pueden editar RUT y/o ID RUPE'))
            else:
                raise osv.except_osv((u'Atención'), ('Imposible crear proveedor. No existe RUT o ID RUPE'))

        else:
            # _logger.info('NO VIENE de "Crear Proveedor GRP"')
            if vals.get('id_rupe',False):
                # Si viene con ID RUPE, debe usar la funcionalidad "Crear Proveedor RUPE"
                raise osv.except_osv((u'Atención'), ('Imposible crear proveedor. Es proveedor RUPE, por lo que debe utilizar la funcionalidad "Crear Proveedor GRP"'))
            else:
                if vals.get('nro_doc_rupe',False) and vals.get('supplier',False):
                    # Viene con RUT
                    # No se permite crear si existe en la staging (lo debe crear a traves de "Crear Proveedor Rupe")
                    prv_rupe_ids = pool_staging_rupe.search(cr, uid, [('prv_cod_fiscal','=',vals.get('nro_doc_rupe',False))], context=context)
                    if prv_rupe_ids:
                        raise osv.except_osv((u'Atención'), ('Imposible crear proveedor. Es proveedor RUPE, por lo que debe utilizar la funcionalidad "Crear Proveedor GRP"'))

        return super(grp_proveedores, self).create(cr, uid, vals, context=context)

grp_proveedores()
