# -*- encoding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################

from openerp import models, fields, api, exceptions, _


class SaleOrderLineAttribute(models.Model):
    _inherit = 'sale.order.line.attribute'

    custom_value = fields.Float(string='Custom value')
    attr_type = fields.Selection(string='Type', store=False,
                                 related='attribute.attr_type')

    def _is_custom_value_in_value_range(self, value, custom_value):
        return (value.min_range <= custom_value <= value.max_range)
    
    def _get_value_from_custom_value(self, custom_value):
        if not self.attr_type == 'range':
            return False
        
        for value in self.possible_values:
            if self._is_custom_value_in_value_range(value, custom_value):
                return value
        return False

    @api.one
    @api.constrains('custom_value', 'attr_type', 'value')
    def _custom_value_in_range(self):
        if self.attr_type == 'range' and not self._is_custom_value_in_value_range(self.value, self.custom_value):
            raise exceptions.Warning(
                _("Custom value for attribute '%s' must be between %s and"
                  " %s.")
                % (self.attribute.name, self.value.min_range,
                   self.value.max_range))

    @api.one
    @api.onchange('value')
    def _onchange_value(self):
        if self.attr_type == 'range' and not self._is_custom_value_in_value_range(self.value, self.custom_value):
            self.custom_value = False
    
    @api.onchange('custom_value')
    def _onchange_custom_value(self):
        if self.attr_type != 'range' or self._is_custom_value_in_value_range(self.value, self.custom_value):
            return
        
        new_value = self._get_value_from_custom_value(self.custom_value)
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


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.one
    def _check_line_confirmability(self):
        for line in self.product_attributes:
            if line.value:
                continue
            attribute_line = self.product_template.attribute_line_ids.filtered(
                lambda x: x.attribute_id == line.attribute)
            if attribute_line.required:
                raise exceptions.Warning(
                    _("You cannot confirm before configuring all values "
                      "of required attributes. Product: %s Attribute: %s.") %
                    (self.product_template.name, attribute_line.display_name))
