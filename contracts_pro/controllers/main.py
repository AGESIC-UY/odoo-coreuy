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

from openerp.http import Controller, route, request
from openerp.addons.web.controllers.main import _serialize_exception
from openerp.osv import osv
from openerp.tools import html_escape
from openerp.addons.report.controllers.main import ReportController
from openerp import http
import simplejson
import logging
from werkzeug import url_decode

# Modification to change file name and language
class HookedReportController(ReportController):


    #------------------------------------------------------
    # Report controllers
    #------------------------------------------------------
    @route([
        '/report/<path:converter>/<reportname>',
        '/report/<path:converter>/<reportname>/<docids>',
    ], type='http', auth='user', website=True)
    def report_routes(self, reportname, docids=None, converter=None, **data):
        """Hook to change language, using resume language
        :param reportname:
        :param docids:
        :param converter:
        :param data:
        :return:
        """
        report_obj = request.registry['report']
        cr, uid, context = request.cr, request.uid, request.context

        if docids:
            docids = [int(i) for i in docids.split(',')]

        options_data = None
        if data.get('options'):
            options_data = simplejson.loads(data['options'])
        if data.get('context'):
            # Ignore 'lang' here, because the context in data is the one from the webclient *but* if
            # the user explicitely wants to change the lang, this mechanism overwrites it.
            data_context = simplejson.loads(data['context'])
            if data_context.get('lang'):
                del data_context['lang']
            context.update(data_context)

        # Hook to set specific language for report content
        # ----------- Hook begin ----- #
        ctx=context.copy()
        model=request.registry['ir.actions.report.xml'].search_read(cr, uid, [('report_name','=',reportname)], ['model'], context=context)
        model_name=model and model[0]['model']
        model_obj=request.registry[model_name]
        # If model prepared to hook report lang, get lang to use
        if hasattr(model_obj, 'get_report_lang_code'):
            lang_code=model_obj.get_report_lang_code(cr, uid, docids[0], context=context)
            if lang_code:
                ctx['lang']=lang_code
        # ----------- End ------------#

        if converter == 'html':
            html = report_obj.get_html(cr, uid, docids, reportname, data=options_data, context=ctx)
            return request.make_response(html)
        elif converter == 'pdf':
            pdf = report_obj.get_pdf(cr, uid, docids, reportname, data=options_data, context=ctx)
            pdfhttpheaders = [('Content-Type', 'application/pdf'), ('Content-Length', len(pdf))]
            return request.make_response(pdf, headers=pdfhttpheaders)
        else:
            raise exceptions.HTTPException(description='Converter %s not implemented.' % converter)


    @route(['/report/download'], type='http', auth="user")
    def report_download(self, data, token):
        """Hook to change file name, using employee/partner name and resume format
        """
        requestcontent = simplejson.loads(data)
        url, type = requestcontent[0], requestcontent[1]
        try:
            if type == 'qweb-pdf':
                reportname = url.split('/report/pdf/')[1].split('?')[0]
                docids = None
                if '/' in reportname:
                    reportname, docids = reportname.split('/')

                if docids:
                    # Generic report:
                    response = self.report_routes(reportname, docids=docids, converter='pdf')
                else:
                    # Particular report:
                    data = url_decode(url.split('?')[1]).items()  # decoding the args represented in JSON
                    response = self.report_routes(reportname, converter='pdf', **dict(data))

                # ----- Hook to rename file -------
                model=request.registry['ir.actions.report.xml'].search_read(request.cr, request.uid, [('report_name','=',reportname)], ['model', 'report_file'], context=request.context)
                model_name=model and model[0]['model']
                model_obj=request.registry[model_name]
                # If model prepared to hook report filename, get filename to use
                if hasattr(model_obj, 'get_report_filename'):
                     # Set specific filename
                    record_ids=[int(id) for id in docids.split(",")]
                    reportfile_prefix=model[0]['report_file']
                    report_file=model_obj.get_report_filename(request.cr, request.uid, record_ids, reportfile_prefix, context=request.context)
                    reportname=report_file or reportfile_prefix
                # ----- End --------------------------

                response.headers.add('Content-Disposition', 'attachment; filename=%s.pdf;' % reportname)
                response.set_cookie('fileToken', token)
                return response
            elif type =='controller':
                reqheaders = Headers(request.httprequest.headers)
                response = Client(request.httprequest.app, BaseResponse).get(url, headers=reqheaders, follow_redirects=True)
                response.set_cookie('fileToken', token)
                return response
            else:
                return
        except Exception, e:
            se = _serialize_exception(e)
            error = {
                'code': 200,
                'message': "Odoo Server Error",
                'data': se
            }
            return request.make_response(html_escape(simplejson.dumps(error)))


