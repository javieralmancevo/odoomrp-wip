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
    
    @api.multi
    def _get_procurement_line_for_actualized(self, template, value, production_proc_lines):
        if value.attr_type == 'range':
            #first checking if they share the same value
            proc_line = production_proc_lines.filtered(lambda l: l.value == value)
            if proc_line:
                return proc_line
            
            #otherwise checking if the custom value fits in some other value
            proc_line = production_proc_lines.filtered(lambda l: l.attribute == value.attribute_id)
            return template.get_value_from_custom_value(value.attribute_id, proc_line.custom_value)
        
        return super(MrpBom, self)._get_procurement_line_for_actualized(template, value, production_proc_lines)

