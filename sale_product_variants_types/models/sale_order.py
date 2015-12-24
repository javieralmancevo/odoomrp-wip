# -*- encoding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################

from openerp import models, fields, api, exceptions, _


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    
    #def _attributes_values_dict_map(self, sale_attribute_line):
    #    res = super(SaleOrderLine, self)._attributes_values_dict_map(sale_attribute_line)
    #    res.update({'custom_value': sale_attribute_line.custom_value})
    #    return res

    @api.one
    def _check_line_confirmability(self):
        for line in self.product_attributes:
            if line.value:
                continue
            attribute_line = self.product_template_id.attribute_line_ids.filtered(
                lambda x: x.attribute_id == line.attribute)
            if attribute_line.required:
                raise exceptions.Warning(
                    _("You cannot confirm before configuring all values "
                      "of required attributes. Product: %s Attribute: %s.") %
                    (self.product_template_id.name, attribute_line.display_name))

