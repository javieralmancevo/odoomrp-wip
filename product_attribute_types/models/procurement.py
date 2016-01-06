# -*- encoding: utf-8 -*-

from openerp import models, fields, api, _


class ProcurementAttributeLine(models.Model):
    _inherit = 'procurement.attribute.line'
    
    custom_value = fields.Float(
        string='Numeric Value', digits=(12, 6))
    attr_type = fields.Selection(
        string='Attribute Type', store=False,
        related='attribute.attr_type')
    
    @api.model
    def _is_custom_value_in_range(self):
        self.ensure_one()
        return self.value.min_range <= self.custom_value <= self.value.max_range
    
    @api.model
    def _get_value_for_range(self):
        self.ensure_one()
        if not self.attr_type == 'range':
            return False
        
        for value in self.possible_values:
            if value.min_range <= self.custom_value <= value.max_range:
                return value
        return False

    @api.one
    @api.constrains('custom_value', 'attr_type', 'value')
    def _custom_value_in_range(self, custom_types=None):
        if custom_types:
            new_custom_types = ['range'] + custom_types
        else:
            new_custom_types = ['range']
        if self.attr_type in new_custom_types and not self._is_custom_value_in_range():
            raise exceptions.Warning(
                _("Custom value for attribute '%s' must be between %s and"
                  " %s.")
                % (self.attribute.name, self.value.min_range,
                   self.value.max_range))

    @api.one
    @api.onchange('value')
    def _onchange_value(self, custom_types=None):
        if custom_types:
            new_custom_types = ['range'] + custom_types
        else:
            new_custom_types = ['range']
        if self.attr_type in new_custom_types and not self._is_custom_value_in_range():
            self.custom_value = False
    
    @api.onchange('custom_value')
    def _onchange_custom_value(self, custom_types=None):
        if custom_types:
            new_custom_types = ['range'] + custom_types
        else:
            new_custom_types = ['range']
        if self.attr_type not in new_custom_types or self._is_custom_value_in_range():
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
        res = super(ProcurementAttributeLine, self).get_data_dict()
        res.update({
            'custom_value': self.custom_value,
        })
        return res
    
    @api.multi
    def equal(self, line):
        res = super(ProcurementAttributeLine, self).equal(line)
        
        if res and (self.attr_type != 'range' or self.custom_value == line.custom_value):
            return True
        return False

