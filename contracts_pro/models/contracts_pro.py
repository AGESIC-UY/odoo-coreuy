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

import base64
import datetime
import dateutil.relativedelta as relativedelta
import lxml
import urlparse
from datetime import date, datetime
from datetime import timedelta
from openerp.osv.orm import setup_modifiers
from openerp.tools.safe_eval import safe_eval as eval
import logging
from openerp.tools.translate import _
from openerp import tools, api, modules
from openerp import SUPERUSER_ID, tools
from openerp.osv import osv, fields
from urllib import urlencode, quote as quote
from openerp.exceptions import ValidationError

from openerp.fields import Date


_logger = logging.getLogger(__name__)


def format_tz(pool, cr, uid, dt, tz=False, format=False, context=None):
    context = dict(context or {})
    if tz:
        context['tz'] = tz or pool.get('res.users').read(cr, SUPERUSER_ID, uid, ['tz'])['tz'] or "UTC"
    timestamp = datetime.datetime.strptime(dt, tools.DEFAULT_SERVER_DATETIME_FORMAT)

    ts = fields.datetime.context_timestamp(cr, uid, timestamp, context)

    if format:
        return ts.strftime(format)
    else:
        lang = context.get("lang")
        lang_params = {}
        if lang:
            res_lang = pool.get('res.lang')
            ids = res_lang.search(cr, uid, [("code", "=", lang)])
            if ids:
                lang_params = res_lang.read(cr, uid, ids[0], ["date_format", "time_format"])
        format_date = lang_params.get("date_format", '%B-%d-%Y')
        format_time = lang_params.get("time_format", '%I-%M %p')

        fdate = ts.strftime(format_date)
        ftime = ts.strftime(format_time)
        return "%s %s%s" % (fdate, ftime, (' (%s)' % tz) if tz else '')

try:
    # We use a jinja2 sandboxed environment to render mako templates.
    # Note that the rendering does not cover all the mako syntax, in particular
    # arbitrary Python statements are not accepted, and not all expressions are
    # allowed: only "public" attributes (not starting with '_') of objects may
    # be accessed.
    # This is done on purpose: it prevents incidental or malicious execution of
    # Python code that may break the security of the server.
    from jinja2.sandbox import SandboxedEnvironment
    mako_template_env = SandboxedEnvironment(
        block_start_string="<%",
        block_end_string="%>",
        variable_start_string="${",
        variable_end_string="}",
        comment_start_string="<%doc>",
        comment_end_string="</%doc>",
        line_statement_prefix="%",
        line_comment_prefix="##",
        trim_blocks=True,               # do not output newline after blocks
        autoescape=True,                # XML/HTML automatic escaping
    )
    mako_template_env.globals.update({
        'str': str,
        'quote': quote,
        'urlencode': urlencode,
        'datetime': datetime,
        'len': len,
        'abs': abs,
        'min': min,
        'max': max,
        'sum': sum,
        'filter': filter,
        'reduce': reduce,
        'map': map,
        'round': round,

        # dateutil.relativedelta is an old-style class and cannot be directly
        # instanciated wihtin a jinja2 expression, so a lambda "proxy" is
        # is needed, apparently.
        'relativedelta': lambda *a, **kw : relativedelta.relativedelta(*a, **kw),
    })
except ImportError:
    _logger.warning("jinja2 not available, templating features will not work!")




# Contract templates
class contracts_pro_template(osv.osv):
    _name = "contracts_pro.template"
    _description='Contract template'
    _inherit=['mail.thread']

    def _get_model_name(self, cr, uid, ids, field_name=None, arg=None, context=None ):

        result = dict.fromkeys(ids)
        for record in self.browse(cr, uid, ids, context=context):
            result[record.id]= record.model_id and record.model_id.model or False
        return result

    _columns={
        'name': fields.char('Name', size=100, required=True),
        'active': fields.boolean('Active?'),
        'effective_date': fields.date('Effective date'),
        'comments': fields.text('Comments'),
        'model_id': fields.many2one('ir.model', 'Model'),
        'model_name': fields.related('model_id', 'model', type='char', string='Model name', store=True),
        'rel_model': fields.function(_get_model_name, type='char', string='Model name'), #Related with problems!!!
        'intro_clause_id': fields.many2one('contracts_pro.clause', 'Introduction clause'),
        'clause_ids': fields.one2many('contracts_pro.template_clause', 'template_id', string='Contract clauses')
    }
    _defaults={
        'effective_date': lambda *a: fields.date.today(),
        'active': True
    }
    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'You cannot have multiple records with same name!'),
    ]

    def _get_mixed_content(self, cr, uid, contract, clause, content, context=None):

        if context is None:
            context = {}

        try:
            template = mako_template_env.from_string(tools.ustr(content))
        except Exception:
            _logger.exception("Template:"+contract.contract_template_id.name+", Failed to load clause: "+clause.name+", content: %r", content)
            return False

        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        variables = {
            'format_tz': lambda dt, tz=False, format=False, context=context: format_tz(self.pool, cr, uid, dt, tz, format, context),
            'user': user,
            'ctx': context,  # context kw would clash with mako internals
            'object': contract
        }
        try:
            render_result = template.render(variables)
        except Exception:
            _logger.exception("Failed to render template %r using values %r" % (template, variables))
            render_result = u""
        if render_result == u"False":
            render_result = u""

        return render_result

    def get_intro_clause(self, cr, uid, template_id, contract_id, context=None):

        if not contract_id or not template_id:
            return False

        data={}

        # Mix clauses content with fields information
        contract_template=self.browse(cr, uid, template_id, context=context)
        if not contract_template or not contract_template.rel_model:
            return False
        contract=self.pool.get(contract_template.rel_model).browse(cr, uid, contract_id, context=context)

        #Intro clause
        if contract and contract.contract_template_id==contract_template and contract_template.intro_clause_id:
            new_content=self._get_mixed_content(cr, uid, contract, contract_template.intro_clause_id, contract_template.intro_clause_id.content, context=context )
            data={
                'type': 'intro',
                'section': contract_template.intro_clause_id.section_id,
                'title': contract_template.intro_clause_id.title,
                'content': new_content
            }
        return data

    def get_clauses_completed(self, cr, uid, template_id, contract_id, section_id=False, context=None):

        if not contract_id or not template_id:
            return False

        # Mix clauses content with fields information
        contract_template=self.browse(cr, uid, template_id, context=context)
        if not contract_template or not contract_template.rel_model:
            return False

        contract=self.pool.get(contract_template.rel_model).browse(cr, uid, contract_id, context=context)
        result=[]
        if contract.contract_template_id==contract_template:
            for clause_row in contract_template.clause_ids:
                if clause_row.clause_id.section_id and clause_row.clause_id.section_id.id==section_id or not section_id:
                    new_content=self._get_mixed_content(cr, uid, contract, clause_row.clause_id, clause_row.clause_id.content, context=context )
                    data={
                        'type': 'clause',
                        'sequence': clause_row.sequence,
                        'clause_nbr': clause_row.clause_nbr,
                        'section': clause_row.clause_id.section_id,
                        'title': clause_row.clause_id.title,
                        'content': new_content
                    }
                    result.append(data)

            #Sort results by sequence
            result=sorted(result, key=lambda elem: elem['sequence'])


        return result

    def get_sections(self, cr, uid, template_id, context=None):

        template=self.browse(cr, uid, template_id, context=context)
        sections={}
        for clause_row in template.clause_ids:
            section_id=clause_row.clause_id.section_id
            if section_id:
                if section_id in sections:
                    if sections[section_id]['sequence']>clause_row.sequence:
                        sections[section_id]=clause_row.sequence
                else:
                    sections[section_id]=clause_row.sequence
        section_list=[{'section_id': key, 'sequence': val} for key,val in sections.iteritems()]
        return [elem['section_id'] for elem in sorted(section_list, key=lambda elem: elem['sequence'])]

    def get_report_filename(self, cr, uid, template_ids, reportfile='', context=None):

        if not template_ids:
            return False

        templates=self.browse(cr, uid, template_ids, context=context)
        if len(template_ids)>1:
            initials=[]
            for template in templates:
                name = template.name
                initials.append("".join([word[0] for word in name.split()]) )
            str_initials="-".join(initials)
            reportname=reportfile+" "+ str_initials
        else:
            reportname=reportfile+" - "+(templates.name)
        return reportname
contracts_pro_template()



# Template Related Clauses
class contracts_pro_template_clause(osv.osv):
    _name = "contracts_pro.template_clause"
    _description='Template related clauses'

    _columns={
        'template_id': fields.many2one('contracts_pro.template', 'Contract template', required=True),
        'sequence': fields.integer('Sequence', required=True),
        'clause_nbr': fields.char('Clause number', size=50),
        'clause_id': fields.many2one('contracts_pro.clause', 'Clause', required=True),
        'comments': fields.text('Comments'),
    }
contracts_pro_template_clause()


# Template Clauses
class contracts_pro_clause(osv.osv):
    _name = "contracts_pro.clause"
    _description='Clauses'
    _inherit=['mail.thread']

    def _get_name(self, cr, uid, ids, field_name=None, arg=None, context=None ):

        result = dict.fromkeys(ids)
        for record in self.browse(cr, uid, ids, context=context):
            name = (record.section_id and (record.section_id.name +": ") or '') + record.title + ( record.version and " (" + record.version + ") " )
            result[record.id]= name
        return result

    def _get_template_ids(self, cr, uid, ids, field_name=None, arg=None, context=None):

        result = dict.fromkeys(ids)
        template_obj=self.pool.get('contracts_pro.template_clause')
        for record in self.browse(cr, uid, ids, context=context):
            template_ids=template_obj.search(cr, uid, [('clause_id','=',record.id)], context=context)
            result[record.id]=[templ_clause.template_id.id for templ_clause in template_obj.browse(cr, uid, template_ids, context=context)]
        return result

    _columns={
        'name': fields.char('Name', size=150, required=True ),
        'state': fields.selection((('draft','Draft'),('to_approve','To Review'),('done','Approved'),('old','Old version'),),string='State', required=True, track_visibility='onchange'),
        'version': fields.char('Version', size=20),
        'original_clause_id': fields.many2one('contracts_pro.clause', 'Original clause'),
        'section_id': fields.many2one('contracts_pro.section', 'Section'),
        'title': fields.char('Title', size=200, translate=True),
        'active': fields.boolean('Active?'),
        'effective_date': fields.date('Effective date'),
        'content': fields.text('Content', translate=True),
        'default_sequence': fields.integer('Default Sequence'),
        'template_ids': fields.function(_get_template_ids, type='many2many', relation='contracts_pro.template', string='Templates')
    }
    _defaults={
        'effective_date': lambda *a: fields.date.today(),
        'active': True,
        'state': 'draft'
    }

    def set_to_approve(self, cr, uid, id, context=None):

        self.write(cr, uid, id, {'state':'to_approve'}, context=context)

    def set_to_done(self, cr, uid, id, context=None):

        self.write(cr, uid, id, {'state':'done'}, context=context)

    def set_to_draft(self, cr, uid, id, context=None):

        self.write(cr, uid, id, {'state':'draft'}, context=context)
contracts_pro_clause()


# Sections
class contracts_pro_section(osv.osv):
    _name = "contracts_pro.section"
    _description='Sections'

    _columns={
        'name': fields.char('Name', size=100, required=True, translate=True),
    }
contracts_pro_section()


# Formulas
class contracts_pro_formula(osv.osv):
    _name = "contracts_pro.formula"
    _description='Metric formulas'

    _columns={
        'name': fields.char('Name', size=100, required=True),
        'code': fields.char('Code', size=50, required=True),
        'formula': fields.text('Formula', required=True),
        'active': fields.boolean('Active?'),
        'effective_date': fields.date('Effective Date'),
        'last_update': fields.date('Last update'),
        'description': fields.text('Description'),
        'current_value': fields.float('Current value', digits=(12,6)),
        'metric_age_tolerance': fields.integer('Age tolerance (days)'),
        'metric_ids': fields.many2many('contracts_pro.metric', 'contracts_pro_formula_metric_rel', 'formula_id', 'metric_id', string='Used Metrics'),
        'value_history_ids': fields.one2many('contracts_pro.formula_history_value', 'formula_id', 'History'),
    }

    _defaults={
        'effective_date': lambda *a: fields.date.today(),
        'active': True
    }

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'You cannot have multiple records with same code!'),
    ]

    def button_update_value(self, cr, uid, formula_id, context=None):
        self.update_value(cr, uid, formula_id, False, context=context)

    def update_value(self, cr, uid, formula_id, evaluation_date=False, context=None):

        if not evaluation_date:
            evaluation_date=datetime.now().date().strftime('%Y-%m-%d')
        if isinstance(evaluation_date, date):
            evaluation_date=evaluation_date.strftime('%Y-%m-%d')


        new_value=self.get_value(cr, uid, formula_id, base_date=evaluation_date, context=context)

        formula=self.browse(cr, uid, formula_id, context=context)

        # Create a new history row for old value and date
        date_value=formula.last_update or evaluation_date
        value_data={
            'formula_id': formula.id,
            'value': formula.current_value,
            'date':date_value
        }
        #Check if history value for date exists, if exists update it otherwise create it
        values_obj=self.pool.get('contracts_pro.formula_history_value')
        value_id=values_obj.search(cr, uid, [('formula_id','=',formula.id),('date','=',date_value)], context=context)
        if not value_id:
            value_data['value']=new_value
            values_obj.create(cr, uid, value_data, context=context)
        else:
            values_obj.write(cr, uid, value_id, value_data, context=context)


        # Update value, and last update
        new_data={
            'current_value': new_value,
            'last_update': evaluation_date
        }

        self.write(cr, uid, [formula.id], new_data, context=context)

        return new_value

    def get_value(self, cr, uid, formula_id, base_date=False, context=None):


        class BrowsableObject(object):
            def __init__(self, pool, cr, uid, formula_id, context, dict):
                self.pool = pool
                self.cr = cr
                self.uid = uid
                self.formula_id = formula_id
                self.formula=self.pool.get('contracts_pro.formula').browse(cr, uid, formula_id) or False
                self.dict = dict
                self.context=context

            def __getattr__(self, attr):
                return attr in self.dict and self.dict.__getitem__(attr) or 0.0

        class Metrics(BrowsableObject):
            """a class that will be used into the python code, mainly for usability purposes"""

            # Service functions

            # Last value for a metric in a period
            def get_last_metric_value(self, metric_code, period, base_date=False):
                values=self.get_metric_values(metric_code, period, base_date)
                return values and values[-1]['value']

            # Average of values for a metric in a period
            def get_avg_metric_value(self, metric_code, period, base_date=False):
                values=self.get_metric_values(metric_code, period, base_date)
                value_sum=values and sum([elem['value'] for elem in values]) or 0
                value_cnt=len(values)
                return value_cnt and value_sum/value_cnt or 0

            # First value for a metric in a period
            def get_first_metric_value(self, metric_code, period, base_date=False):
                values=self.get_metric_values(metric_code, period, base_date)
                return values and values[0]['value']

            # Variation value for a metric in a period
            def get_metric_value_variation(self, metric_code, period, base_date=False):
                result=0
                values=self.get_metric_values(metric_code, period, base_date)
                if values:
                    first_date=values[0]['date']
                    res=self.get_previous_metric_value(metric_code, first_date)
                    if not res:
                        raise osv.except_osv(_('Error!'),_('Evaluating metric: ')+metric_code+_(', no previous value for defined period'))
                    first=res['value']
                    last=values[-1]['value']
                    result= last-first
                return result

            # Variation factor between 0 and 1 for a metric in a period
            def get_metric_value_variation_prc(self, metric_code, period, base_date=False):
                result=0
                values=self.get_metric_values(metric_code, period, base_date)
                if values:
                    first_date=values[0]['date']
                    res=self.get_previous_metric_value(metric_code, first_date)
                    if not res:
                        raise osv.except_osv(_('Error!'),_('Evaluating metric: ')+metric_code+_(', no previous value for defined period'))
                    first=res['value']
                    last=values[-1]['value']
                    result=first and (last-first)/first
                return result or 0

            # Minimum value for a metric in a period
            def get_min_metric_value(self, metric_code, period, base_date=False):
                values=self.get_metric_values(metric_code, period, base_date)
                min_value=values and min([elem['value'] for elem in values]) or 0
                return min_value

            # Maximum value for a metric in a period
            def get_max_metric_value(self, metric_code, period, base_date=False):
                values=self.get_metric_values(metric_code, period, base_date)
                max_value=values and max([elem['value'] for elem in values]) or 0
                return max_value

            # Returns an ascending ordered by date list of dictionaries with 'value' and 'date' elements, inside a period for a specific metric
            def get_metric_values(self, metric_code, period_code, base_date=False):

                # Check period and metric codes
                period_obj=self.pool.get('contracts_pro.period')
                period_id=period_obj.search(self.cr, self.uid, [('code','=',period_code)], context=self.context)
                if not period_id:
                    raise osv.except_osv(_('Error!'),_('Period code not found'))
                metric_obj=self.pool.get('contracts_pro.metric')
                metric_id=metric_obj.search(self.cr, self.uid, [('code','=',metric_code)], context=self.context)
                if not metric_id:
                    raise osv.except_osv(_('Error!'),_('Metric code not found'))

                # Get period limits
                base_date=base_date or datetime.now().date()
                period=period_obj.browse(self.cr, self.uid, period_id, context=self.context)
                start_period, end_period = period_obj.get_period_limits_from_date(self.cr, self.uid, [period.id], base_date)

                # Get historic values for period
                values_obj=self.pool.get('contracts_pro.metric_history_value')
                values_ids=values_obj.search(self.cr, self.uid, [('date','>=',start_period),('date','<=',end_period),('metric_id','=',metric_id[0])], order='date', context=self.context)
                values=[ {'value': elem.value, 'date': elem.date} for elem in values_obj.browse(self.cr, self.uid, values_ids, context=self.context) ]

                return values

            # Returns previous value to a reference date
            def get_previous_metric_value(self, metric_code, reference_date ):

                metric_obj=self.pool.get('contracts_pro.metric')
                metric_id=metric_obj.search(self.cr, self.uid, [('code','=',metric_code)], context=self.context)
                if not metric_id:
                    raise osv.except_osv(_('Error!'),_('Metric code not found'))

                # Get previous value
                values_obj=self.pool.get('contracts_pro.metric_history_value')
                filter=reference_date and [('date','<',reference_date),('metric_id','=',metric_id[0])] or [('metric_id','=',metric_id[0])]
                values_ids=values_obj.search(self.cr, self.uid, filter, order='date desc', limit=1, context=self.context)
                if values_ids:
                    elem=values_obj.browse(self.cr, self.uid, values_ids, context=self.context)
                    return {'value': elem.value, 'date': elem.date}
                return False


        # Base date or today
        base_date=base_date or datetime.now().date().strftime('%Y-%m-%d')

        # Get related metrics
        formula=self.browse(cr, uid, formula_id, context=context)
        metrics=formula.metric_ids
        metrics_dict=self.pool.get('contracts_pro.metric').read(cr, uid, [el.id for el in metrics], context=context)

        # Check last updates for related metrics and max age tolerance
        if formula.metric_age_tolerance:
            for item in metrics_dict:
                if not item['last_update']:
                    raise osv.except_osv(_('Error!'), _('La variable no tiene fecha de actualización alguna definida'))
                dt_last_update= datetime.strptime(item['last_update'],'%Y-%m-%d').date()
                dt_evaluation_date= datetime.strptime(base_date,'%Y-%m-%d').date()
                # If older than tolerance, return error
                if (dt_evaluation_date-dt_last_update).days>formula.metric_age_tolerance:
                    raise osv.except_osv(_('Error!'),_('Last value older than tolerance for metric: '+item['name']))

        # Create object to browse in formula code
        metrics_obj = Metrics(self.pool, cr, uid, formula.id, context, metrics_dict)

        # Put objects in dictionary to be used by rules
        baselocaldict = {'metrics': metrics_obj}
        localdict = dict(baselocaldict, formula=formula, base_date=base_date, metric_objects=metrics, context=context)

        for var in localdict['metric_objects']:
            base_date_formatted = Date.from_string(base_date)
            if not var.value_history_ids.filtered(lambda x: Date.from_string(x.date) == base_date_formatted):
                raise ValidationError(
                    _("La variable %s no tiene valores definidos para la fecha %s y está siendo usada en la fórmula!") % (var.name, base_date_formatted))
        # Evaluate formula and get result
        try:
            eval(formula.formula, localdict, mode='exec', nocopy=True)
            if 'result' in localdict:
                value=localdict['result']
            else:
                value={}
        except Exception:
            raise osv.except_osv(_('Error!'),_('Evaluation formula code: '+formula.name))


        return value
contracts_pro_formula()


# Metrics
class contracts_pro_metric(osv.osv):
    _name = "contracts_pro.metric"
    _description='Metric'

    def _get_current_info(self, cr, uid, ids, field_name=None, arg=None, context=None ):

        result = dict.fromkeys(ids)
        for record in self.browse(cr, uid, ids, context=context):
            result[record.id]={'current_value': False, 'last_update': False}

            # Get current value
            today=datetime.now().date().strftime('%Y-%m-%d')
            values_obj=self.pool.get('contracts_pro.metric_history_value')
            value_id=values_obj.search(cr, uid, [('metric_id','=',record.id),('date','<=',today)], order='date desc',limit=1, context=context)
            if value_id:
                value=values_obj.browse(cr, uid, value_id, context=context)
                result[record.id]={'current_value':value.value, 'last_update':value.date}

        return result

    _columns={
        'name': fields.char('Name', size=100, required=True),
        'code': fields.char('Code', size=50, required=True),
        'active': fields.boolean('Active?'),
        'last_update': fields.function(_get_current_info, multi='current', type='date', string='Last update'),
        'current_value': fields.function(_get_current_info, multi='current', type='float', string='Current value'),
        'description': fields.text('Description'),
        'value_history_ids': fields.one2many('contracts_pro.metric_history_value', 'metric_id', 'History'),
    }

    _defaults={
        'active': True
    }

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'You cannot have multiple records with same code!'),
    ]
contracts_pro_metric()


# Formula history values
class contracts_pro_formula_history_value(osv.osv):
    _name = "contracts_pro.formula_history_value"
    _description='Metric'
    _order="date desc"

    _columns={
        'formula_id': fields.many2one('contracts_pro.formula', 'Formula', required=True),
        'date': fields.date('Date'),
        'value': fields.float('Value', digits=(12,6)),
    }
    _sql_constraints = [
        ('date_val_formula_uniq', 'unique(formula_id,date,value)', 'You cannot have multiple records with same formula-date-value!'),
    ]
contracts_pro_formula_history_value()


# Metric history values
class contracts_pro_metric_history_value(osv.osv):
    _name = "contracts_pro.metric_history_value"
    _description='Metric'
    _order='date desc'

    _columns={
        'metric_id': fields.many2one('contracts_pro.metric', 'Metric', required=True),
        'date': fields.date('Date'),
        'value': fields.float('Value', digits=(12,6)),
    }
    _sql_constraints = [
        ('date_val_metric_uniq', 'unique(metric_id,date,value)', 'You cannot have multiple records with same metric-date-value!'),
    ]
contracts_pro_metric_history_value()


# Model for new version Wizard
class contracts_pro_new_version(osv.osv_memory):
    _name='contracts_pro.new_version'
    _description='Clause new version wizard'

    _columns={
        'new_version_name': fields.char('Version name', size=50, required=True),
        'clause_id': fields.many2one('contracts_pro.clause', 'Clause', required=True)
    }

    def create_new_version(self, cr, uid, id, context=None):
        wizard=self.browse(cr, uid, id, context=context)
        if wizard and wizard.new_version_name:
            clause_obj=self.pool.get('contracts_pro.clause')
            new_version_name=wizard.new_version_name
            clause_id=wizard.clause_id.id
            clause=clause_obj.browse(cr, uid, clause_id, context=context)

            # Create a clause copy of original, but as an old version
            new_id=clause_obj.copy(cr, uid, clause_id, {'state': 'old', 'version': clause.version, 'active': False, 'original_clause_id': clause_id} , context=context)

            # Change version on original clause and put state to draft (to keep original references to clause intact)
            today=datetime.now().date().strftime('%Y-%m-%d')
            clause_obj.write(cr, uid, clause_id, {'version': new_version_name, 'state': 'draft', 'effective_date': today}, context=context)

            result = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'contracts_pro', 'contracts_pro_clauses_action')

            id = result and result[1] or False
            result = self.pool.get('ir.actions.act_window').read(cr, uid, [id], context=context)[0]
            result['res_id']=clause_id

            return result

        return True
contracts_pro_new_version()


# Time periods
class contracts_pro_period(osv.osv):
    _name="contracts_pro.period"


    def _calc_period_limits(self, year_fixed_start, year_relative_start, month_fixed_start, month_relative_start, day_fixed_start, day_relative_start, year_fixed_end, year_relative_end, month_fixed_end, month_relative_end, day_fixed_end, day_relative_end, date_base):


        def _calc_new_date(date_base, relative_year, relative_month, relative_day, fixed_year, fixed_month, fixed_day):

            new_year=fixed_year or date_base.year    #Start with specified year or current
            new_month=fixed_month or date_base.month#Start with specified month or current
            new_day = fixed_day or date_base.day      #Start with specified day or current

            if relative_month:
                relative_month_sign=relative_month<0 and -1 or 1
                new_year+= relative_month_sign * (abs(relative_month)//12)   # If relative months > 12 impact year
                new_month+= relative_month_sign * (abs(relative_month) % 12)     # Get only the module for relative months and apply to current month
                if new_month<=0:
                    new_month = 12 + new_month     # Correct to past year if new_month <=0
                    new_year-=1
                elif new_month>12:
                    new_month = new_month % 12      # Correct to past year if new_month <=0
                    new_year+=1

            new_year = relative_year and new_year + relative_year or new_year     # If relative year <0 adjust year

            new_day = new_day>30 and new_month not in (1,3,5,7,8,10,12) and 30 or new_day   # Correct day if > 30 in 30 day months
            new_day = new_day>29 and new_month == 2 and 29 or new_day                       # Correct day if > 29 in february, to 29

            try:
                new_date=date(new_year, new_month, new_day)
            except:
                new_date=date(new_year, new_month, 28)          # In case year is not bisiest

            if relative_day:
                new_date+=timedelta(days=relative_day)

            return new_date

        start_date=_calc_new_date(date_base, year_relative_start, month_relative_start, day_relative_start, year_fixed_start, month_fixed_start, day_fixed_start)
        end_date=_calc_new_date(date_base, year_relative_end, month_relative_end, day_relative_end, year_fixed_end, month_fixed_end, day_fixed_end)

        return (start_date, end_date)

    def _get_period_limits(self, cr, uid, ids, field_name=None, arg=None, context=None):

        strdate=context.get('base_date', date.today().strftime('%Y-%m-%d') )
        base_date=datetime.strptime(strdate,'%Y-%m-%d').date()
        result = dict.fromkeys(ids)
        for record in self.browse(cr, uid, ids, context=context):

            result[record.id]={}
            res_date_start,res_date_end=self._calc_period_limits(record.year_fixed_start, record.year_relative_start, record.month_fixed_start, record.month_relative_start, record.day_fixed_start, record.day_relative_start, record.year_fixed_end,record.year_relative_end, record.month_fixed_end,record.month_relative_end, record.day_fixed_end,record.day_relative_end, base_date)
            result[record.id]['date_start']=res_date_start.strftime('%Y-%m-%d')
            result[record.id]['date_end']=res_date_end.strftime('%Y-%m-%d')

        return result

    def get_period_limits_from_date(self, cr, uid, ids, base_date, context=None):

        base_date=isinstance(base_date, str) and datetime.strptime(base_date,'%Y-%m-%d').date() or base_date
        result = dict.fromkeys(ids)
        for record in self.browse(cr, uid, ids, context=context):

            result[record.id]={}
            res_date_start,res_date_end=self._calc_period_limits(record.year_fixed_start, record.year_relative_start, record.month_fixed_start, record.month_relative_start, record.day_fixed_start, record.day_relative_start, record.year_fixed_end,record.year_relative_end, record.month_fixed_end,record.month_relative_end, record.day_fixed_end,record.day_relative_end, base_date)
            str_date_start=res_date_start.strftime('%Y-%m-%d')
            str_date_end=res_date_end.strftime('%Y-%m-%d')

        return (str_date_start, str_date_end )


    _columns={
        'name': fields.char('Name', size=50, required=True),
        'code': fields.char('Code',required=True),
        'year_relative_start': fields.integer('Year relative'),
        'year_fixed_start': fields.integer('Year fixed'),
        'month_relative_start': fields.integer('Month relative'),
        'month_fixed_start': fields.integer('Month fixed'),
        'day_relative_start': fields.integer('Day relative'),
        'day_fixed_start': fields.integer('Day fixed'),
        'year_relative_end': fields.integer('Year relative'),
        'year_fixed_end': fields.integer('Year fixed'),
        'month_relative_end': fields.integer('Month relative'),
        'month_fixed_end': fields.integer('Month fixed'),
        'day_relative_end': fields.integer('Day relative'),
        'day_fixed_end': fields.integer('Day fixed'),
        'date_base_example': fields.date('Base date example'),
        'date_start': fields.function(_get_period_limits, multi='date_limits', type='date', string='Start'),
        'date_end': fields.function(_get_period_limits, multi='date_limits', type='date', string='End'),
    }

    _defaults={
        'day_relative_start': 1,
        'month_relative_start': 1,
        'year_relative_start': 0,
        'day_relative_end': 0,
        'month_relative_end': 0,
        'year_relative_end': 0,
        'date_base_example': lambda *a: fields.date.today()

    }

    def on_change_date(self, cr, uid, period_id, year_fixed_start, year_relative_start, month_fixed_start, month_relative_start, day_fixed_start, day_relative_start, year_fixed_end, year_relative_end, month_fixed_end, month_relative_end, day_fixed_end, day_relative_end, date_base_example):

        if month_relative_start>12 or month_relative_end>12:
            raise osv.except_osv(_('Error!'),_('Fixed month must be between 1 and 12'))
        if day_relative_start>31 or day_relative_end>31:
            raise osv.except_osv(_('Error!'),_('Fixed day cannot be greater than 31'))
        values={}
        #values['day_fixed_start']=day_relative_start or day_fixed_start
        #values['month_fixed_start']=month_relative_start or month_fixed_start
        #values['year_fixed_start']=year_relative_start or year_fixed_start

        #values['day_fixed_end']=day_relative_end or day_fixed_end
        #values['month_fixed_end']=month_relative_end or month_fixed_end
        #values['year_fixed_end']=year_relative_end or year_fixed_end

        date_base=datetime.strptime(date_base_example, '%Y-%m-%d').date()
        date_start, date_end = self._calc_period_limits(year_fixed_start, year_relative_start, month_fixed_start, month_relative_start, day_fixed_start, day_relative_start, year_fixed_end, year_relative_end, month_fixed_end, month_relative_end, day_fixed_end, day_relative_end, date_base)
        values['date_start']=date_start.strftime('%Y-%m-%d')
        values['date_end']=date_end.strftime('%Y-%m-%d')

        return {'value': values}
contracts_pro_period()



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
