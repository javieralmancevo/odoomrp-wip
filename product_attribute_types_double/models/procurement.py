# -*- encoding: utf-8 -*-

from openerp import models, fields, api, _

import logging
_logger = logging.getLogger(__name__)


class ProcurementAttributeLine(models.Model):
    _inherit = 'procurement.attribute.line'
    
    custom_value_second = fields.Float(
        string='Second Numeric Value', digits=(12, 6))
    
    @api.multi
    def _is_second_custom_value_in_range(self):
        self.ensure_one()
        return self.value.min_range_second <= self.custom_value_second <= self.value.max_range_second
    
    @api.model
    def _get_value_for_range(self):
        self.ensure_one()
        if self.attr_type == 'double_range':
            for value in self.possible_values:
                if value.min_range <= self.custom_value <= self.value.max_range and \
                        value.min_range_second <= self.custom_value_second <= value.max_range_second:
                    return value
            return False
        return super(ProcurementAttributeLine)._get_value_for_range()
    
    @api.one
    @api.constrains('custom_value', 'attr_type', 'value')
    def _custom_value_in_range(self, custom_types=None):
        if custom_types:
            new_custom_types = ['double_range'] + custom_types
        else:
            new_custom_types = ['double_range']
        super(ProcurementAttributeLine, self)._custom_value_in_range(custom_types=new_custom_types)
    
    @api.one
    @api.constrains('custom_value_second', 'attr_type', 'value')
    def _custom_value_second_in_range(self, custom_types=None):
        if custom_types:
            new_custom_types = ['double_range'] + custom_types
        else:
            new_custom_types = ['double_range']
        if self.attr_type in new_custom_types and not self. _is_second_custom_value_in_range():
            raise exceptions.Warning(
                _("Second custom value for attribute '%s' are not within"
                  " range.")
                % (self.attribute.name))
    
    @api.one
    @api.onchange('value')
    def _onchange_value(self, custom_types=None):
        if custom_types:
            new_custom_types = ['double_range'] + custom_types
        else:
            new_custom_types = ['double_range']
        super(ProcurementAttributeLine, self)._onchange_value(custom_types=new_custom_types)
        if self.attr_type == 'double_range':
            if not self._is_second_custom_value_in_range():
                self.custom_value_second = False
    
    @api.onchange('custom_value')
    def _onchange_custom_value(self, custom_types=None):
        if custom_types:
            new_custom_types = ['double_range'] + custom_types
        else:
            new_custom_types = ['double_range']
        super(ProcurementAttributeLine, self)._onchange_custom_value(custom_types=new_custom_types)
    
    @api.onchange('custom_value_second')
    def _onchange_custom_value_second(self, custom_types=None):
        if custom_types:
            new_custom_types = ['double_range'] + custom_types
        else:
            new_custom_types = ['double_range']
        if self.attr_type not in new_custom_types or self._is_second_custom_value_in_range():
            return
        
        new_value = self._get_value_for_range()
        if new_value:
            self.value = new_value
        else:
            self.custom_value = None
            return {
                'warning': {
                    'title': _("Out of range"),
                    'message': _("Custom value for attribute '%s' is out of any value range.") % (self.attribute.name),
                },
            }
    
    @api.multi
    def get_data_dict(self):
        self.ensure_one()
        res = super(ProcurementAttributeLine, self).get_data_dict()
        res.update({
            'custom_value_second': self.custom_value_second,
        })
        return res

