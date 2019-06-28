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


class poblar_codigueras_sice(osv.osv_memory):
    _name = 'poblar.codigueras.sice'
    _columns = {
        'name': fields.char('Descripcion', size=200),
    }

    def poblar_codigueras(self, cr, uid, ids=None, context=None):
        module_path = '/opt/odoo/custom/addons/grp_compras_estatales/dat/'

        # DocumentosProveedor
        dic = {}
        with open(module_path + 'DocumentosProveedor.csv') as f:
            for line in f:
                field = line.split(';')
                dic['tipoDocProv'] = field[0]
                dic['descTipoDocProv'] = field[1]
                dic['proveedorRupe'] = field[2]
                dic['propioTesoreria'] = field[3]
                dic['formato'] = field[4]
                dic['pcpd'] = field[5]
                self.pool.get('sicec.doc.proveedor').create(cr, uid, dic, context=context)


        # Estados Compra
        dic = {}
        with open(module_path + 'EstadosCompra.csv') as f:
            for line in f:
                field = line.split(';')
                dic['codEstado'] = field[0]
                dic['descEstado'] = field[1]
                self.pool.get('sicec.estado.compra').create(cr, uid, dic, context=context)


        # Monedas
        dic = {}
        with open(module_path + 'Monedas.csv') as f:
            for line in f:
                field = line.split(';')
                dic['codMoneda'] = field[0]
                dic['descMoneda'] = field[1]
                self.pool.get('sicec.moneda').create(cr, uid, dic, context=context)


        # Incisos Ejecutoras Compra
        with open(module_path + 'IncisosEjecutorasCompra.csv') as f:
            for line in f:
                dic = {}
                field = line.split(';')

                # De acuerdo al tipo de línea
                if field[0][0:2] == 'IN':
                    dic['idInciso'] = field[1]
                    dic['descInciso'] = field[2]
                    idInciso = self.pool.get('sicec.inciso').create(cr, uid, dic, context=context)

                elif field[0][0:2] == 'UE':
                    dic['idInciso'] = idInciso
                    dic['idUE'] = field[1]
                    dic['descUE'] = field[2]
                    idUE = self.pool.get('sicec.ue').create(cr, uid, dic, context=context)

                elif field[0][0:2] == 'UC':
                    dic['idInciso'] = idInciso
                    dic['idUE'] = idUE
                    dic['idUC'] = field[1]
                    dic['descUC'] = field[2]
                    dic['interrelacionSIIF'] = field[3]
                    idUC = self.pool.get('sicec.uc').create(cr, uid, dic, context=context)

                else:
                    pass


        # Tipo Subtipo Compra
        with open(module_path + 'TipoSubTipoCompra.csv') as f:
            for line in f:
                dic = {}
                field = line.split(';')

                # De acuerdo al tipo de línea
                if field[0][0:2] == 'TC':
                    dic['idTipoCompra'] = field[1]
                    dic['descTipoCompra'] = field[2]
                    dic['interrelacionSIIF'] = field[3]
                    dic['comprasCentralizadas'] = field[4]
                    dic['ofertaEconomica'] = field[5]
                    dic['plazoMinOferta'] = field[6]
                    dic['actoApertura'] = field[7]
                    dic['resolucionObligatoria'] = field[8]
                    dic['solicitudesLlamado'] = field[9]
                    dic['ampliaciones'] = field[10]
                    dic['topeLegal'] = field[11]
                    dic['pcpd'] = field[12]
                    idTipo = self.pool.get('sicec.tipo.compra').create(cr, uid, dic, context=context)

                elif field[0][0:2] == 'SC':
                    dic['idTipoCompra'] = idTipo
                    dic['idSubtipoCompra'] = field[2]
                    dic['descSubtipoCompra'] = field[3]
                    dic['comprasCentralizadas'] = field[4]
                    dic['fondosRotatorios'] = field[5]
                    dic['publicacionLlamado'] = field[6]
                    dic['condPrecioOfertas'] = field[7]
                    dic['validaRupe'] = field[8]
                    idSubtipo = self.pool.get('sicec.subtipo.compra').create(cr, uid, dic, context=context)

                else:
                    pass

        return


poblar_codigueras_sice()
