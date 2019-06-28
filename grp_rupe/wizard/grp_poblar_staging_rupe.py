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

import re
import csv
import pdb
from openerp.osv import osv, fields
from openerp.modules import get_module_path
import logging

_logger = logging.getLogger(__name__)


class poblar_staging_rupe(osv.osv_memory):
    """Wizard que carga el staging del RUPE en OpenERP"""
    _name = 'poblar.staging.rupe'
    _columns = {
        'name': fields.char('Descripcion', size=200),
    }

    def poblar_staging_rupe(self, cr, uid, ids=None, context=None):
        """
        Se leen los datos almacenados en los archivos CSV provistos
        por RUPE y con ellos se realiza una réplica en tablas OpenERP
        que servirán como staging para los datos de proveedores.
       """

        # Tratamiento segun el tipo de dato
        def char_value(valor):
            return valor

        def datetime_value(valor):

            # Sin datos ...
            if not valor: return None

            # Cambiar diagonal por guion
            valor = re.sub('/', '-', valor)

            # Si tiene milesimas, eliminarlas
            valor = re.sub('\..+', '', valor)

            # En caso de faltar los segundos, anadirlos
            if valor.count(':') == 1:
                valor = valor + ':00'

            return valor

        def integer_value(valor):
            numero = int(float(valor)) if valor else None
            return numero

        def date_value(valor):
            # Sin datos ...
            if not valor: return None
            # Cambiar diagonal por guion
            valor = re.sub('/', '-', valor)
            return valor


        # Los tipos de datos considerados
        type_value = {
            'char': char_value,
            'datetime': datetime_value,
            'integer': integer_value,
            'date': date_value,
        }

        # Archivos CSV provistos por ACCE
        csv_file_list = [
            # 'rupe_cuentas_bancarias.csv',
            # 'rupe_datos_comunicacion_proveedor.csv',
            # 'rupe_proveedores.csv',
        ]

        # Ubicación en el FileSystem
        module_path = get_module_path(self._module) + '/dat/'
        cr.execute(""" SET datestyle = 'ISO, DMY' """)
        tablas_no_pobladas = []

        # Para cada archivo CSV
        for csv_file in csv_file_list:
            try:
                _logger.info('CSV FILE: %s',csv_file)

                f = open(module_path + csv_file)

                # El modelo OSV
                osv_class = self.pool.get(csv_file.replace('.csv', '').replace('_', '.'))

                # Si ya tiene datos no se hace nada
                if osv_class.search(cr, uid, [], count=True):
                    tablas_no_pobladas.append(csv_file.replace('.csv', '').replace('_', '.'))
                    continue

                try:
                    # Stream al CSV
                    csv_stream = csv.DictReader(f, delimiter=';')

                    # Para cada linea en el stream
                    for linea in csv_stream:

                        # Los datos para osv_class
                        osv_data = {}

                        # Para cada campo
                        for campo in csv_stream.fieldnames:
                            # ¿ Está en la clase ?
                            if campo in osv_class._columns:
                                # El tipo de la columna
                                tipo = type(osv_class._columns[campo]).__name__
                                # El valor "preparado"
                                osv_data[campo] = type_value[tipo](linea[campo])

                        # Grabar la línea en la clase
                        osv_class.create(cr, uid, osv_data)

                except csv.Error as e_csv:
                    print "GRP_ERROR: ", e_csv

                finally:
                    f.close()

            except (IOError, OSError) as e_open:
                print "GRP_ERROR: ", e_open

        if len(tablas_no_pobladas) > 0:
            mensaje = 'Carga realizada correctamente. Las siguientes tablas fueron omitidas ya que poseen datos cargados: '
            lista = ""
            for tabla in tablas_no_pobladas:
                lista += tabla + ', '

            mensaje = mensaje + lista

            return {
                'type': 'ir.actions.client',
                'tag': 'action_warn',
                'name': 'Aviso',
                'target': 'current',
                'context': context,
                'params': {
                    'title': 'Aviso',
                    'text': mensaje,
                    'sticky': True
                }}
        return


poblar_staging_rupe()
