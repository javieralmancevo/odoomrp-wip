# -*- coding: utf-8 -*-
from openerp import models, fields, api, _


class MrpBom(models.Model):
    _inherit='mrp.bom'
    
    @api.multi
    def _get_new_line_dict_from_proc_line(self, template, proc_line, production_proc_lines):
        self.ensure_one()
        
        res = super(MrpBom, self)._get_new_line_dict_from_proc_line(template, proc_line, production_proc_lines)
        
        if proc_line.attr_type == 'range':
            attribute_line = template.attribute_line_ids.filtered(lambda al: al.attribute_id == proc_line.attribute)
            if not attribute_line: #should never happen
                raise exceptions.Error(_('Could not find an attribute line in template for asigned procurement attribute line.'))
            
            #first checking if they share the same value, if they do not share the same value, search for one that fits the custom_value
            if not attribute_line.value_ids.filtered(lambda v: v == proc_line.value):
                new_value = attribute_line.value_ids.filtered(lambda v: v.min_range <= proc_line.custom_value and v.max_range >= proc_line.custom_value)
                if new_value:
                    res['value'] = new_value[0].id
                else:
                    raise exceptions.Warning(_('Custom value outside the range of any attribute value.'))
            
            res['custom_value'] = proc_line.custom_value
        
        return res

