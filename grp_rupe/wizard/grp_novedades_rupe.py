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
import os
import time
import datetime
from openerp.osv import osv, fields
from suds.client import Client
from datetime import date, timedelta

_logger = logging.getLogger(__name__)

# logging.basicConfig(level=logging.INFO)
# logging.getLogger('suds.client').setLevel(logging.DEBUG)
# logging.getLogger('suds.transport').setLevel(logging.DEBUG)
# logging.getLogger('suds.xsd.schema').setLevel(logging.DEBUG)
# logging.getLogger('suds.wsdl').setLevel(logging.DEBUG)


class wizard_novedades_rupe(osv.osv_memory):
    """Wizard que carga las novedades de Proveedores
       en el staging de RUPE en OpenERP"""

    _name = 'wizard.novedades.rupe'
    _columns = {
        'name': fields.char('Descripcion', size=200),
    }

    # Las URLs de los WS de novedades y datos de proveedores
    key_novedades = "grp_rupe.novedades_wsdl"
    url_novedades = "_http://"

    key_datos = "grp_rupe.datos_proveedor_wsdl"
    url_datos = "_http://"

    # Usuarios para servicios de novedades y consulta
    key_usr_novedades = "grp_rupe.usr_novedades"
    key_usr_datos = "grp_rupe.usr_datos"
    usr_novedades = ""
    usr_datos = ""

    # Indicar si Proceso de Novedades Rupe debe estar corriendo
    key_procesar_novedades_rupe = "grp_rupe_novedades.activo"
    val_procesar_novedades_rupe = "True"

    # Parámetro del sistema: Cantidad de días registro de errores del proceso de novedades RUPE
    key_rupe_dias_error_log = "grp_rupe_novedades.dias_error_log"
    val_rupe_dias_error_log = "90"

    # Parámetro del sistema: Cantidad de días registro del proceso de novedades RUPE
    key_rupe_dias_log = "grp_rupe_novedades.dias_log"
    val_rupe_dias_log = "90"

    # Los objetos SOAP para la conexión
    ws_novedades = None
    ws_datos = None

    def configurar_novedades_rupe(self, cr, uid, ids=None, context=None):
        """
        Se dan de alta la tarea planificada y las URLs de los WS de novedades
        y datos de proveedores.

        La tarea planificada se crea con loas siguientes características:
            Nombre: La identificación de la tarea
            Activo: False (Para que el administrador la active)
            Repetir períodos: False (Para que los atrasados no se ejecuten)
            Intervalo: weeks
            Veces de invocación: -1 (para que se ejecute siempre))
            Usuario: El usuario que instala el módulo (valor por defecto)
            Demás valores: default de la clase ir.cron

        Las URLs de los WS
            Se dan de alta las de Test pasando a travéz del conector PGE
        """

        # La tarea planificada
        tarea = {}
        tarea['name'] = 'RUPE: Recepcion de Novedades'
        tarea['model'] = 'wizard.novedades.rupe'
        tarea['function'] = 'novedades_rupe'
        tarea['args'] = '()'
        tarea['interval_type'] = 'hours'
        tarea['numbercall'] = -1
        tarea['doall'] = False
        tarea['active'] = False

        cr.execute("select id from ir_cron where name = %(name)s", {'name': tarea['name']})
        if not cr.rowcount:
            self.pool.get('ir.cron').create(cr, uid, tarea, context=context)

        # Parámetros del sistema
        # Las URLs de los WS de novedades y datos de proveedores. Usuarios para servicio de novedades y consulta de datos
        sys_cfg = self.pool.get('ir.config_parameter')
        if not sys_cfg.get_param(cr, uid, self.key_novedades):
            sys_cfg.set_param(cr, uid, self.key_novedades, self.url_novedades)
        if not sys_cfg.get_param(cr, uid, self.key_datos):
            sys_cfg.set_param(cr, uid, self.key_datos, self.url_datos)
        if not sys_cfg.get_param(cr, uid, self.key_procesar_novedades_rupe):
            sys_cfg.set_param(cr, uid, self.key_procesar_novedades_rupe, self.val_procesar_novedades_rupe)

        if not sys_cfg.get_param(cr, uid, self.key_usr_novedades):
            sys_cfg.set_param(cr, uid, self.key_usr_novedades, self.usr_novedades)
        if not sys_cfg.get_param(cr, uid, self.key_usr_datos):
            sys_cfg.set_param(cr, uid, self.key_usr_datos, self.usr_datos)

        # Cantidad de dias de mantenimiento de logs
        if not sys_cfg.get_param(cr, uid, self.key_rupe_dias_error_log):
            sys_cfg.set_param(cr, uid, self.key_rupe_dias_error_log, self.val_rupe_dias_error_log)
        if not sys_cfg.get_param(cr, uid, self.key_rupe_dias_log):
            sys_cfg.set_param(cr, uid, self.key_rupe_dias_log, self.val_rupe_dias_log)

        return True

    def conectar_rupe(self, cr, uid):
        """
        Establece la conexión con los WS y crea los objetos SOAP clientes
        de dicha conexión.
        """

        # Obtener las URLs necesarias de los parámetros del sistema
        sys_cfg = self.pool.get('ir.config_parameter')

        wsdl_datos = sys_cfg.get_param(cr, uid, self.key_datos)
        if not wsdl_datos:
            raise osv.except_osv('Error!',
                                 u'No se encuentra configurada la ruta del WSDL para consumir los datos de los proveedores')

        # Verfico si usa url de conector PGE o archivo wsdl local
        if 'http' not in str(wsdl_datos):
            # en caso de usar archivo wsdl local al addon, deberia ser x ej: '/RUPE_ConsultaProveedores.wsdl'
            path_file = os.path.dirname(os.path.abspath(__file__))
            wsdl_datos = 'file://' + path_file + wsdl_datos

        wsdl_novedades = sys_cfg.get_param(cr, uid, self.key_novedades)
        if not wsdl_novedades:
            raise osv.except_osv('Error!',
                                 u'No se encuentra configurada la ruta del WSDL para consumir las novedades de los proveedores')

        usr_novedades = sys_cfg.get_param(cr, uid, self.key_usr_novedades)
        if not usr_novedades:
            raise osv.except_osv('Error!',
                                 u'No se encuentra configurado en GRP el usuario del servicio de novedades RUPE')
        self.usr_novedades = usr_novedades

        usr_datos = sys_cfg.get_param(cr, uid, self.key_usr_datos)
        if not usr_datos:
            raise osv.except_osv('Error!',
                                 u'No se encuentra configurado en GRP el usuario del servicio de consulta de proveedores RUPE')
        self.usr_datos = usr_datos


        # Verfico si usa url de conector PGE o archivo wsdl local
        if 'http' not in str(wsdl_novedades):
            # en caso de usar archivo wsdl local al addon, deberia ser x ej: '/ProdRecibirNovedadService.wsdl'
            path_file = os.path.dirname(os.path.abspath(__file__))
            wsdl_novedades = 'file://' + path_file + wsdl_novedades


        # Establecer las conexiones
        try:
            self.ws_novedades = Client(wsdl_novedades, cache=None)
            # _logger.info("WS_NOVEDADES: %s", self.ws_novedades)
        except Exception as e:
            self.registar_error_log(cr, uid, 'conectar_rupe', 'wsdl_novedades', str(e))
            return False

        try:
            self.ws_datos = Client(wsdl_datos, cache=None)
            # _logger.info("WS_DATOS: %s", self.ws_datos)
        except Exception as e:
            self.registar_error_log(cr, uid, 'conectar_rupe', 'wsdl_datos', str(e))
            return False

        return True

    def purge_error_log(self, cr, uid):
        """
        Elimina del registro del log de errores aquellos registros mas viejos que la cantidad de dias definido en parámetro del sistema
        """

        # La cantidad de días atrás a mantener el registro de log
        sys_cfg = self.pool.get('ir.config_parameter')
        dias_atras = sys_cfg.get_param(cr, uid, self.key_rupe_dias_error_log)

        if not dias_atras:
            raise osv.except_osv('Error!',
                                 u'No se encuentra configurada la cantidad de días atrás para mantenimiento de logs de errores')
        fecha_min = date.today() - timedelta(days=int(dias_atras))

        # _logger.info('Fecha minima para registros de error_log: %s', fecha_min.strftime("%Y-%m-%d"))
        cr.execute("DELETE FROM rupe_novedades_error_log WHERE date_trunc('day',fecha) < %s", (fecha_min,))

        return

    def purge_proc_log(self, cr, uid):
        """
        Elimina del registro del proceso de novedades aquellos registros mas viejos que la cantidad de dias definido en parámetro del  sistema        Deja registro de las inconsistencias entre las novedades y el staging
        """
        # La cantidad de días atrás a mantener el registro de log
        sys_cfg = self.pool.get('ir.config_parameter')
        dias_atras = sys_cfg.get_param(cr, uid, self.key_rupe_dias_log)

        if not dias_atras:
            raise osv.except_osv('Error!',
                                 u'No se encuentra configurada la cantidad de días atrás para mantenimiento de logs de errores')
        fecha_min = date.today() - timedelta(days=int(dias_atras))

        # _logger.info('Fecha minima para registros de proc log: %s', fecha_min.strftime("%Y-%m-%d"))
        cr.execute("DELETE FROM rupe_historico_novedades WHERE date_trunc('day',fecha_proceso) < %s", (fecha_min,))

        return

    def registar_historico(self, cr, uid, datos, objeto, operacion):
        """
        Recibe:
           datos: diccionario con los datos a aplicar en staging
           objeto: 'PROVEEDOR', 'CUENTA BANCARIA', DATO COMUNICACION'
		   operacion: el codigoOperacion informado por RUPE A-Alta, B-Baja, M-Modificacion
		Inserta en la tabla del modelo rupe_historico_novedades un registro como testigo del proceso de la novedad
        """
        datos_hist = {}
        datos_hist['name'] = objeto
        datos_hist['operacion'] = operacion
        datos_hist['fecha_modificacion'] = datos['ultima_modificacion']

        if objeto == 'PROVEEDOR':
            datos_hist['objeto_id_rupe'] = datos['prv_id']
            datos_hist['prv_id'] = datos['prv_id']

            if datos.has_key('prv_denominacion_social'):
                datos_hist['descripcion'] = datos['prv_denominacion_social']
            elif datos.has_key('prv_nombre_fantasia'):
                datos_hist['descripcion'] = datos['prv_nombre_fantasia']

            datos_hist['version'] = str(datos['prv_version'])
        elif objeto == 'CUENTA BANCARIA':
            datos_hist['objeto_id_rupe'] = datos['cnt_id']
            datos_hist['prv_id'] = datos['cnt_proveedor_prv_id']
            datos_hist['descripcion'] = datos['cnt_nro_cuenta']
            datos_hist['version'] = str(datos['cnt_version'])
        elif objeto == 'DATO COMUNICACION':
            datos_hist['objeto_id_rupe'] = datos['dco_id']
            datos_hist['prv_id'] = datos['dco_proveedor_prv_id']
            if datos.has_key('dco_destino'):
                # _logger.info("dco_destino: %s", datos['dco_destino'])
                datos_hist['descripcion'] = datos['dco_destino']
            datos_hist['version'] = str(datos['dco_version'])

        datos_hist['objeto_id_rupe_str'] = str(datos_hist['objeto_id_rupe'])
        datos_hist['prv_id_str'] = str(datos_hist['prv_id'])

        rupe_hist_nov = self.pool.get('rupe.historico.novedades')
        rupe_hist_nov.create(cr, uid, datos_hist)

    def registar_error_log(self, cr, uid, funcion, operacion, mensaje_error):
        datos_error = {}
        datos_error['funcion'] = funcion
        datos_error['operacion'] = operacion
        datos_error['msg_error_rupe'] = mensaje_error
        rupe_error_log = self.pool.get('rupe.novedades.error.log')
        rupe_error_log.create(cr, uid, datos_error)

    def prv_staging(self, cr, uid, novedad):
        # ¿ Existe el proveedor en el "Staging" ?
        grp_rupe_prov = self.pool.get('rupe.proveedores')
        orm_id = grp_rupe_prov.search(cr, uid, [('prv_id', '=', novedad.proveedorId)])
        if orm_id:
            prv_in_staging = True

            #  En que version ?
            prv_staging_version = grp_rupe_prov.browse(cr, uid, orm_id)[0].prv_version
        else:
            prv_in_staging = False
            prv_staging_version = -1

        return (prv_in_staging, prv_staging_version, grp_rupe_prov, orm_id)

    def dco_staging(self, cr, uid, ncom):
        # ¿ Existe el dato de comunicación en el "Staging" ?
        grp_rupe_dco = self.pool.get('rupe.datos.comunicacion.proveedor')
        orm_id = grp_rupe_dco.search(cr, uid, [('dco_id', '=', ncom.idElementoModificado)])
        if orm_id:
            dco_in_staging = True

            #  En que version ?
            dco_staging_version = grp_rupe_dco.browse(cr, uid, orm_id)[0].dco_version
        else:
            dco_in_staging = False
            dco_staging_version = -1

        return (dco_in_staging, dco_staging_version, grp_rupe_dco, orm_id)

    def cnt_staging(self, cr, uid, ncnt):
        #  Existe el dato de cuenta bancaria en el "Staging" ?
        grp_rupe_cnt = self.pool.get('rupe.cuentas.bancarias')
        orm_id = grp_rupe_cnt.search(cr, uid, [('cnt_id', '=', ncnt.idElementoModificado)])
        if orm_id:
            cnt_in_staging = True
            #  En que version ?
            cnt_staging_version = grp_rupe_cnt.browse(cr, uid, orm_id)[0].cnt_version
        else:
            cnt_in_staging = False
            cnt_staging_version = -1

        return (cnt_in_staging, cnt_staging_version, grp_rupe_cnt, orm_id)

    def procesar_proveedor(self, cr, uid, novedad):
        """
        Procesa la novedad del Proveedor cuando 'soloModificaDatosGenerales'
        """
        res_partner_obj = self.pool.get('res.partner')

        def obtener_datos(self, novedad):
            """
            Carga los datos de la novedad correspondientes al proveedor
            """
            dato_recibido = False
            # Verifico si el proceso debe continuar o finalizar
            sys_cfg = self.pool.get('ir.config_parameter')
            continuar_proceso = sys_cfg.get_param(cr, uid, self.key_procesar_novedades_rupe) == "True"

            while not dato_recibido and continuar_proceso:
                try:
                    # _logger.info("PROVEEDOR_ID: %s", novedad.proveedorId)
                    operacion = "obtenerProveedorID"
                    idProv = self.ws_datos.service.obtenerProveedorID(novedad.proveedorId, self.usr_datos)

                    provEntrada = self.ws_datos.factory.create('obtenerDatosProveedorEntrada')
                    provEntrada['idProveedor'] = idProv

                    # _logger.info("provEntrada: %s", provEntrada)
                    operacion = "obtenerProveedor"
                    prov = self.ws_datos.service.obtenerProveedor(provEntrada, self.usr_datos, novedad.version)

                    _logger.info("Datos Proveedor en RUPE: %s", prov)
                    dato_recibido = True
                    continuar_proceso = sys_cfg.get_param(cr, uid, self.key_procesar_novedades_rupe) == "True"

                except Exception as e:
                    # registro error
                    self.registar_error_log(cr, uid, 'procesar_proveedor.obtener_datos', operacion, str(e))
                    _logger.info("*** Error RUPE: Obtener proveedor responde: %s", str(e))

                    if 'Fault occurred while processing' in str(e):
                        self.registar_error_log(cr, uid, 'procesar_proveedor.obtener_datos', operacion,
                                                'Fault occurred while processing: idProveedor: ' + str(
                                                    novedad.proveedorId))
                        continuar_proceso = False
                        break
                    else:
                        continuar_proceso = sys_cfg.get_param(cr, uid, self.key_procesar_novedades_rupe) == "True"
                        if not continuar_proceso:
                            break
                        _logger.info("*** RUPE Proveedor: Reintento en 1 minuto ***")
                        time.sleep(60)  # delay por 1 minuto
                        continue

            # Preparar diccionario con datos del Proveedor
            datos = {}
            datos_partner = {}

            if not continuar_proceso:
                return (datos, datos_partner)

            if novedad.codigoOperacion == "A":
                if 'fechaVersion' in prov: datos['prv_crea_fecha'] = prov.fechaVersion
                if 'fechaVersion' in prov: datos['dom_crea_fecha'] = prov.fechaVersion

            if 'idProveedor' in prov:
                datos['prv_id'] = prov.idProveedor
                datos_partner['id_rupe'] = prov.idProveedor

            if 'numeroIdentificacion' in prov.identificacionPrincipal:
                datos['prv_cod_fiscal'] = prov.identificacionPrincipal.numeroIdentificacion
                datos_partner['nro_doc_rupe'] = prov.identificacionPrincipal.numeroIdentificacion

            if 'codigoPais' in prov.identificacionPrincipal: datos[
                'codigo_pais'] = prov.identificacionPrincipal.codigoPais

            if 'tipoDocumento' in prov.identificacionPrincipal:
                datos['codigo_tipo_documento'] = prov.identificacionPrincipal.tipoDocumento
                tipo_doc = 'R'
                if prov.identificacionPrincipal.tipoDocumento.strip() == 'RUT':
                    tipo_doc = 'R'
                if prov.identificacionPrincipal.tipoDocumento.strip() == 'CI':
                    tipo_doc = 'CI'
                if prov.identificacionPrincipal.tipoDocumento.strip() == 'PS':
                    tipo_doc = 'PS'
                if prov.identificacionPrincipal.tipoDocumento.strip() == 'NIE':
                    tipo_doc = 'NIE'
                datos_partner['tipo_doc_rupe'] = tipo_doc

            if 'datosRepresentacion' in prov: datos['prv_descripcion_respresentantes'] = prov.datosRepresentacion

            if 'correoElectronicoPrincipal' in prov:
                datos['prv_correo_electronico'] = prov.correoElectronicoPrincipal
                datos_partner['email'] = prov.correoElectronicoPrincipal

            if 'denominacionSocial' in prov:
                datos['prv_denominacion_social'] = prov.denominacionSocial
                datos_partner['name'] = prov.denominacionSocial

            if 'domicilioFiscal' in prov:
                datos['prv_domicilio_fiscal'] = prov.domicilioFiscal
                datos_partner['street'] = prov.domicilioFiscal

            if 'nomLocalidadDomicilioFiscal' in prov:
                datos['prv_loc_fiscal_nombre'] = prov.nomLocalidadDomicilioFiscal
                datos_partner['city'] = prov.nomLocalidadDomicilioFiscal

            if 'nombreFantasia' in prov: datos['prv_nombre_fantasia'] = prov.nombreFantasia

            if 'sitioWeb' in prov: datos['prv_sitio_web'] = prov.sitioWeb

            if 'fechaVersion' in prov:
                datos['prv_ultmod_fecha'] = prov.fechaVersion
                datos_partner['fecha_creacion_rupe'] = prov.fechaVersion
                datos_partner['fecha_modif_rupe'] = prov.fechaVersion

            if 'version' in prov:
                datos['prv_version'] = prov.version
                datos_partner['version_rupe'] = prov.version

            if 'codigoPais' in prov.domicilioNotificacion: datos[
                'dom_codigo_pais'] = prov.domicilioNotificacion.codigoPais
            if 'codigoDepartamento' in prov.domicilioNotificacion: datos[
                'dom_codigo_depto'] = prov.domicilioNotificacion.codigoDepartamento
            if 'dirDeptoExterior' in prov.domicilioNotificacion: datos[
                'dom_depto_exterior'] = prov.domicilioNotificacion.dirDeptoExterior
            if 'dirCodigoLocalidad' in prov.domicilioNotificacion: datos[
                'dom_codigo_local'] = prov.domicilioNotificacion.dirCodigoLocalidad
            if 'dirCiudadExterior' in prov.domicilioNotificacion: datos[
                'dom_ciudad_exterior'] = prov.domicilioNotificacion.dirCiudadExterior
            if 'tipoVialidad' in prov.domicilioNotificacion: datos[
                'dom_codigo_tipo_vial'] = prov.domicilioNotificacion.tipoVialidad
            if 'nombreVialidad' in prov.domicilioNotificacion: datos[
                'dom_nombre_vialidad'] = prov.domicilioNotificacion.nombreVialidad
            if 'numeroPuerta' in prov.domicilioNotificacion: datos[
                'dom_nro_puerta'] = prov.domicilioNotificacion.numeroPuerta

            if 'dirBis' in prov.domicilioNotificacion: datos['dom_bis'] = prov.domicilioNotificacion.dirBis

            if 'dirApto' in prov.domicilioNotificacion: datos['dom_apto'] = prov.domicilioNotificacion.dirApto

            if 'CodigoPostal' in prov.domicilioNotificacion: datos[
                'dom_codigo_postal'] = prov.domicilioNotificacion.CodigoPostal
            if 'otraDescripcion' in prov.domicilioNotificacion: datos[
                'dom_descripcion'] = prov.domicilioNotificacion.otraDescripcion
            if 'nombreRuta' in prov.domicilioNotificacion: datos['dom_ruta'] = prov.domicilioNotificacion.nombreRuta
            if 'kilometro' in prov.domicilioNotificacion: datos['dom_kilometro'] = prov.domicilioNotificacion.kilometro
            if 'manzanaCatastral' in prov.domicilioNotificacion: datos[
                'dom_manzana_catastral'] = prov.domicilioNotificacion.manzanaCatastral

            if 'solarCatastral' in prov.domicilioNotificacion: datos[
                'dom_solar_catastral'] = prov.domicilioNotificacion.solarCatastral

            if 'dirCodigoEntradaColectiva' in prov.domicilioNotificacion: datos[
                'dom_desc_tipo_ent_col'] = prov.domicilioNotificacion.dirCodigoEntradaColectiva

            if 'dirNombreInmueble' in prov.domicilioNotificacion: datos[
                'dom_nombre_inmueble'] = prov.domicilioNotificacion.dirNombreInmueble

            if 'paridad' in prov.domicilioNotificacion: datos['dom_codigo_par'] = prov.domicilioNotificacion.paridad
            if 'fechaVersion' in prov: datos['dom_ultmod_fecha'] = prov.fechaVersion

            if 'codDeptoDomicilioFiscal' in prov: datos['codigo_depto_fiscal'] = prov.codDeptoDomicilioFiscal

            if 'estadoDelProveedor' in prov:
                datos['codigo_estado'] = prov.estadoDelProveedor
                datos_partner['estado_rupe'] = prov.estadoDelProveedor

            if 'tipoOrganizacion' in prov: datos['codigo_nat_juridica'] = prov.tipoOrganizacion

            # Marcar como modificado
            datos['modificado'] = True
            datos['ultima_modificacion'] = prov.fechaVersion

            datos_partner['is_company'] = True
            datos_partner['supplier'] = True

            # _logger.info("DATOS PROVEEDOR: %s", datos)
            return (datos, datos_partner)


        # ¿ Existe el proveedor en el "Staging" ?
        prv_in_staging, prv_staging_version, grp_rupe_prov, prv_orm_id = self.prv_staging(cr, uid, novedad)

        # Procesar según operación
        if novedad.codigoOperacion == "A":

            if not prv_in_staging:
                datos, datos_partner = obtener_datos(self, novedad)
                if len(datos) > 0:
                    # Crear proveedor en staging
                    grp_rupe_prov.create(cr, uid, datos)
                    # Registrar historico
                    self.registar_historico(cr, uid, datos, 'PROVEEDOR', 'A')

        elif novedad.codigoOperacion == "B":
            # Se procesa como una modificación que
            # cambia el estado del proveedor a BAJA
            pass

        elif novedad.codigoOperacion == "M":
            if prv_in_staging:
                if prv_staging_version < novedad.version:
                    datos, datos_partner = obtener_datos(self, novedad)
                    if len(datos) > 0:
                        # Actualizar proveedor en staging
                        grp_rupe_prov.write(cr, uid, prv_orm_id, datos)

                        # Actualizar proveedor en res_partner
                        res_partner_id_found = res_partner_obj.search(cr, uid,
                                                                      [('nro_doc_rupe', '=', datos_partner['nro_doc_rupe'])])
                        if res_partner_id_found is not False:
                            # Actualizo proveedor en GRP
                            res_partner_obj.write(cr, uid, res_partner_id_found, datos_partner)

                        # Registro historico
                        if datos['codigo_estado'] == 'BAJA' or datos['codigo_estado'] == 'CANC':
                            self.registar_historico(cr, uid, datos, 'PROVEEDOR', 'B')
                        else:
                            self.registar_historico(cr, uid, datos, 'PROVEEDOR', 'M')
        return True

    def procesar_datos_comunicacion(self, cr, uid, novedad):
        """
        Procesa la novedad de los datos de comunicación del proveedor
        """

        def obtener_datos_comunicacion(self, novedad, ncom):
            """
            Obtiene los datos de una novedad de comunicación
            """
            dato_recibido = False
            # Verifico si el proceso debe continuar o finalizar
            sys_cfg = self.pool.get('ir.config_parameter')
            continuar_proceso = sys_cfg.get_param(cr, uid, self.key_procesar_novedades_rupe) == "True"

            while not dato_recibido and continuar_proceso:
                try:
                    dcom = self.ws_datos.service.obtenerComunicacionPorId(ncom.idElementoModificado, self.usr_datos, ncom.version)

                    _logger.info("Datos de Comunicacion en RUPE: %s", dcom)
                    dato_recibido = True
                    continuar_proceso = sys_cfg.get_param(cr, uid, self.key_procesar_novedades_rupe) == "True"

                except Exception as e:
                    # registro error
                    self.registar_error_log(cr, uid, 'procesar_datos_comunicacion.obtener_datos_comunicacion',
                                            'obtenerComunicacionPorId', str(e))

                    if 'Fault occurred while processing' in str(e):
                        self.registar_error_log(cr, uid, 'procesar_datos_comunicacion.obtener_datos_comunicacion',
                                                'obtenerComunicacionPorId',
                                                'Fault occurred while processing: idComunicacion: ' + str(
                                                    ncom.idElementoModificado) + '|version: ' + str(ncom.version))
                        continuar_proceso = False
                        break
                    else:
                        continuar_proceso = sys_cfg.get_param(cr, uid, self.key_procesar_novedades_rupe) == "True"
                        if not continuar_proceso:
                            break
                        # _logger.info("*** RUPE obtenerComunicacionPorId: Reintento en 1 minuto ***")
                        time.sleep(60)  # delay por 1 minuto
                        continue

            # Datos de la comunicacion
            datos = {}
            if not continuar_proceso:
                return datos

            if ncom.tipoOperacion == "A":
                if 'fechaVersion' in dcom: datos['dco_crea_fecha'] = dcom.fechaVersion

            if 'proveedorId' in novedad: datos['dco_proveedor_prv_id'] = novedad.proveedorId
            if 'idComunicacion' in dcom: datos['dco_id'] = dcom.idComunicacion
            if 'comentario' in dcom: datos['dco_comentario'] = dcom.comentario
            if 'destino' in dcom: datos['dco_destino'] = dcom.destino
            if 'fechaVersion' in dcom: datos['dco_ultmod_fecha'] = dcom.fechaVersion
            if 'version' in dcom: datos['dco_version'] = dcom.version
            if 'tipoComunicacion' in dcom: datos['codigo_tipo_comunic'] = dcom.tipoComunicacion

            # Marcar como modificado
            datos['modificado'] = True
            datos['ultima_modificacion'] = ncom.fechaModificacion

            return datos

        #  Existe el proveedor en el "Staging" ?
        prv_in_staging, prv_staging_version, grp_rupe_prov, prv_orm_id = self.prv_staging(cr, uid, novedad)

        # _logger.info("prv_in_staging: %s ", prv_in_staging)
        # _logger.info("prv_staging_version: %s", prv_staging_version)

        if prv_in_staging:

            # Para cada novedad de comunicacion
            for una_ncom in novedad.comunicacionesModificadas.elementosModificados:

                #  Existe este dato de comunicacióon el staging ?
                dco_in_staging, dco_staging_version, grp_rupe_dco, dco_orm_id = self.dco_staging(cr, uid, una_ncom)

                # Segun tipo de operacion ...
                if una_ncom.tipoOperacion == "A":
                    if not dco_in_staging:
                        datos = obtener_datos_comunicacion(self, novedad, una_ncom)
                        if len(datos) > 0:
                            grp_rupe_dco.create(cr, uid, datos)
                            # Registro historico
                            self.registar_historico(cr, uid, datos, 'DATO COMUNICACION', 'A')

                elif una_ncom.tipoOperacion == "B":
                    if dco_in_staging:
                        datos = obtener_datos_comunicacion(self, novedad, una_ncom)
                        if len(datos) > 0:
                            datos['active'] = False
                            grp_rupe_dco.write(cr, uid, dco_orm_id, datos)
                            # Registro historico
                            self.registar_historico(cr, uid, datos, 'DATO COMUNICACION', 'B')

                elif una_ncom.tipoOperacion == "M":
                    if dco_in_staging:
                        if dco_staging_version < una_ncom.version:
                            datos = obtener_datos_comunicacion(self, novedad, una_ncom)
                            if len(datos) > 0:
                                grp_rupe_dco.write(cr, uid, dco_orm_id, datos)
                                # Registro historico
                                self.registar_historico(cr, uid, datos, 'DATO COMUNICACION', 'M')

        return True

    def procesar_cuentas_bancarias(self, cr, uid, novedad):
        """
        Procesa la novedad de las cuentas bancarias del proveedor
        """

        def obtener_cuenta_bancaria(self, novedad, ncnt):
            """
            Obtiene los datos de una novedad de cuenta bancaria
            """
            dato_recibido = False
            # Verifico si el proceso debe continuar o finalizar
            sys_cfg = self.pool.get('ir.config_parameter')
            continuar_proceso = sys_cfg.get_param(cr, uid, self.key_procesar_novedades_rupe) == "True"

            while not dato_recibido and continuar_proceso:
                try:
                    dcnt = self.ws_datos.service.obtenerCuentaBancariaPorId(ncnt.idElementoModificado, self.usr_datos, ncnt.version)

                    _logger.info("Datos de Cuenta Bancaria en RUPE: %s", dcnt)
                    dato_recibido = True
                    continuar_proceso = sys_cfg.get_param(cr, uid, self.key_procesar_novedades_rupe) == "True"

                except Exception as e:
                    # registro error
                    self.registar_error_log(cr, uid, 'procesar_cuentas_bancarias.obtener_cuenta_bancaria',
                                            'obtenerCuentaBancariaPorId', str(e))
                    # _logger.info("*** Error RUPE: Cuenta Bancaria responde: %s", str(e))

                    if 'Fault occurred while processing' in str(e):
                        self.registar_error_log(cr, uid, 'procesar_cuentas_bancarias.obtener_cuenta_bancaria',
                                                'obtenerCuentaBancariaPorId',
                                                'Fault occurred while processing: idCuentaBancaria: ' + str(
                                                    ncnt.idElementoModificado) + '|version: ' + str(ncnt.version))
                        continuar_proceso = False
                        break
                    else:
                        continuar_proceso = sys_cfg.get_param(cr, uid, self.key_procesar_novedades_rupe) == "True"
                        if not continuar_proceso:
                            break
                        # _logger.info("*** RUPE obtenerCuentaBancariaPorId: Reintento en 1 minuto ***")
                        time.sleep(60)  # delay por 1 minuto
                        continue

            # Datos de la cuenta bancaria
            datos = {}
            if not continuar_proceso:
                return datos

            if ncnt.tipoOperacion == "A":
                # En "dcnt" estan los valores retornados por el servicio web y en "datos" se cargan los mismos con clave los nombres de fields
                if 'idCuentaBancaria' in dcnt: datos['cnt_id'] = dcnt.idCuentaBancaria
                if 'proveedorId' in novedad: datos['cnt_proveedor_prv_id'] = novedad.proveedorId
                if 'fechaVersion' in dcnt: datos['cnt_crea_fecha'] = dcnt.fechaVersion
            if ncnt.tipoOperacion == "B":
                datos['active'] = False

            # Modificaciones + Alta
            # agrego cnt_id y cnt_proveedor_prv_id pues detecte novedades de "M" sin la existencia de la cuenta bancaria en la base de datos
            if 'idCuentaBancaria' in dcnt: datos['cnt_id'] = dcnt.idCuentaBancaria
            if 'proveedorId' in novedad: datos['cnt_proveedor_prv_id'] = novedad.proveedorId

            if 'fechaVersion' in dcnt: datos['cnt_ultmod_fecha'] = dcnt.fechaVersion
            if 'codigoBanco' in dcnt: datos['codigo_banco'] = dcnt.codigoBanco
            if 'nombreBanco' in dcnt: datos['cnt_nombre_banco'] = dcnt.nombreBanco
            if 'codigoSucursal' in dcnt: datos['codigo_sucursal'] = dcnt.codigoSucursal
            if 'nombreSucursal' in dcnt: datos['nombre_sucursal'] = dcnt.nombreSucursal
            if 'nombreSucursal' in dcnt: datos['cnt_sucursal'] = dcnt.nombreSucursal
            if 'numeroCuenta' in dcnt: datos['cnt_nro_cuenta'] = dcnt.numeroCuenta
            if 'moneda' in dcnt: datos['codigo_moneda'] = dcnt.moneda
            if 'tipoCuenta' in dcnt: datos['codigo_tipo_cuenta'] = dcnt.tipoCuenta
            if 'codigoSWIFT' in dcnt: datos['cnt_codigo_swift'] = dcnt.codigoSWIFT
            if 'codigoABA' in dcnt: datos['cnt_numero_aba'] = dcnt.codigoABA
            if 'codigoPais' in dcnt: datos['codigo_pais'] = dcnt.codigoPais
            if 'nombreTitularDeLaCuenta' in dcnt: datos['cnt_titular_cuenta'] = dcnt.nombreTitularDeLaCuenta
            if 'codigoPaisBancoIntermediario' in dcnt: datos['codigo_pais_int'] = dcnt.codigoPaisBancoIntermediario
            if 'nombreBancoIntermediario' in dcnt: datos['cnt_nombre_banco_intermedio'] = dcnt.nombreBancoIntermediario
            if 'codigoSWIFTBancoIntermediario' in dcnt: datos[
                'cnt_codigo_swift_banco_intermedio'] = dcnt.codigoSWIFTBancoIntermediario
            if 'ciudadBancoIntermediario' in dcnt: datos[
                'cnt_ciudad_banco_intermediario'] = dcnt.ciudadBancoIntermediario
            if 'ciudadBanco' in dcnt: datos['cnt_ciudad_banco'] = dcnt.ciudadBanco
            if 'direccionBanco' in dcnt: datos['cnt_direccion_banco_destino'] = dcnt.direccionBanco
            if 'codigoIBAN' in dcnt: datos['cnt_iban'] = dcnt.codigoIBAN
            if 'version' in dcnt: datos['cnt_version'] = dcnt.version

            # Marcar como modificado
            datos['modificado'] = True
            datos['ultima_modificacion'] = ncnt.fechaModificacion

            return datos

        #  Existe el proveedor en el "Staging" ?
        prv_in_staging, prv_staging_version, grp_rupe_prov, prv_orm_id = self.prv_staging(cr, uid, novedad)

        if prv_in_staging:

            # Para cada novedad de cuentas bancarias
            for una_ncnt in novedad.cuentasBancariasModificadas.elementosModificados:

                #  Existe este dato de cuenta bancaria en el staging ?
                cnt_in_staging, cnt_staging_version, grp_rupe_cnt, cnt_orm_id = self.cnt_staging(cr, uid, una_ncnt)

                # Segun tipo de operacion ...
                if una_ncnt.tipoOperacion == "A":

                    if not cnt_in_staging:

                        datos = obtener_cuenta_bancaria(self, novedad, una_ncnt)

                        if len(datos) > 0:

                            grp_rupe_cnt.create(cr, uid, datos)
                            # Registro historico
                            self.registar_historico(cr, uid, datos, 'CUENTA BANCARIA', 'A')

                elif una_ncnt.tipoOperacion == "B":

                    if cnt_in_staging:

                        datos = obtener_cuenta_bancaria(self, novedad, una_ncnt)

                        if len(datos) > 0:

                            grp_rupe_cnt.write(cr, uid, cnt_orm_id, datos)
                            # Registro historico
                            self.registar_historico(cr, uid, datos, 'CUENTA BANCARIA', 'B')

                elif una_ncnt.tipoOperacion == "M":

                    if cnt_in_staging:

                        if cnt_staging_version < una_ncnt.version:

                            datos = obtener_cuenta_bancaria(self, novedad, una_ncnt)
                            if len(datos) > 0:
                                # _logger.info("datos: %s", datos)

                                grp_rupe_cnt.write(cr, uid, cnt_orm_id, datos)
                                # Registro historico
                                self.registar_historico(cr, uid, datos, 'CUENTA BANCARIA', 'M')

                    else:

                        # Proveedor Existe, pero no la cuenta a pesar de que viene para Modificar, Se procesa como Alta.
                        datos = obtener_cuenta_bancaria(self, novedad, una_ncnt)
                        if len(datos) > 0:

                            grp_rupe_cnt.create(cr, uid, datos)
                            # Registro historico
                            self.registar_historico(cr, uid, datos, 'CUENTA BANCARIA', 'A')

        return True

    def novedades_rupe(self, cr, uid, ids=None, context=None):
        """
        Se consumen las novedades mediante el WS correspondiente y se actualiza el staging en caso de ser novedad de:
            - Datos generales del Proveedor
            - Datos de comunicacion
            - Datos de Cuentas bancarias
        """
        _logger.info("NOVEDADES RUPE: INICIO")
        # purge de logs
        self.purge_error_log(cr, uid)
        self.purge_proc_log(cr, uid)

        # Establecer la conexión
        if not self.conectar_rupe(cr, uid):
            self.registar_error_log(cr, uid, 'novedades_rupe', 'conectar_rupe', 'No se pudo conectar con el servicio')
            return False

        # Consumo de novedades
        enterado = 0
        novedad = False

        # Verifico si el proceso debe continuar o finalizar
        sys_cfg = self.pool.get('ir.config_parameter')
        continuar_proceso = sys_cfg.get_param(cr, uid, self.key_procesar_novedades_rupe) == "True"

        while continuar_proceso:
            try:
                # Test
                # novedad =  self.ws_novedades.service.recibirNovedad(self.usr_novedades, 'AcceRupeNovedadesProveedores', enterado)

                # Prod
                novedad = self.ws_novedades.service.recibirNovedad(self.usr_novedades, 'NovedadesProveedores', enterado)

                if not novedad:
                    self.registar_error_log(cr, uid, 'novedades_rupe', 'recibirNovedad', 'Sin novedad para procesar')
                    return True

                # Obtengo Id de Notificacion (para que en la proxima solicitud, ésta novedad quede marcada como procesada
                enterado = self.ws_novedades.last_received().getChild("soap:Envelope").getChild("soap:Header").getChild(
                    "notificationId").getText()

            except Exception as e:
                # Verificar si se alcanzo la ultima novedad
                if "'NoneType' object has no attribute 'getText'" in str(e):
                    # En caso de no recibirse notification_id (se alcanzó la última novedad), finalizar proceso
                    return True
                else:
                    # registro error
                    self.registar_error_log(cr, uid, 'novedades_rupe', 'recibirNovedad', str(e))

                    continuar_proceso = sys_cfg.get_param(cr, uid, self.key_procesar_novedades_rupe) == "True"
                    if not continuar_proceso:
                        return True
                    else:
                        time.sleep(60)  # delay por 1 minuto
                        continue

            # # Terminamos ?
            if not 'proveedorId' in novedad:
                self.registar_error_log(cr, uid, 'novedades_rupe', 'recibirNovedad', 'Sin novedad para procesar')
                return True

            # Tipo de novedad ?
            if novedad.soloModificaDatosGenerales:
                _logger.info('NOVEDAD RUPE PROVEEDOR: %s', novedad)
                self.procesar_proveedor(cr, uid, novedad)
                _logger.info('FIN PROCESO: PROVEEDOR')

            elif 'comunicacionesModificadas' in novedad:
                _logger.info('NOVEDAD RUPE DATOS COMUNICACION: %s', novedad)
                self.procesar_datos_comunicacion(cr, uid, novedad)
                _logger.info('FIN PROCESO: DATOS COMUNICACION')

            elif 'cuentasBancariasModificadas' in novedad:
                _logger.info('NOVEDAD RUPE CUENTAS BANCARIAS: %s', novedad)
                self.procesar_cuentas_bancarias(cr, uid, novedad)
                _logger.info('FIN PROCESO: CUENTAS BANCARIAS')
            else:
                _logger.info('NOVEDAD RUPE NO CONTEMPLADA: %s', novedad)

            cr.commit()

            continuar_proceso = sys_cfg.get_param(cr, uid, self.key_procesar_novedades_rupe) == "True"

        _logger.info("NOVEDADES RUPE: FIN")
        return True

wizard_novedades_rupe()
