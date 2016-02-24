# -*- coding: utf-8 -*-
from openerp import models, fields, api, _


class MrpBom(models.Model):
    _inherit='mrp.bom'
    
    @api.multi
    def _get_new_line_dict_from_proc_line(self, template_id, proc_line, production_proc_lines):
        self.ensure_one()
        
        res = super(MrpBom, self)._get_new_line_dict_from_proc_line(template_id, proc_line, production_proc_lines)
        
        if proc_line.attr_type == 'range':
            res['custom_value'] = proc_line.custom_value
        
        return res

