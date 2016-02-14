# -*- encoding: utf-8 -*-

from openerp import models, fields, api, _


class ProductAttribute(models.Model):
    _inherit = "product.attribute"
    
    attr_type = fields.Selection(
        required=True, selection=[
            ('select', 'Select'),
            ('range', 'Range'),
            ('numeric', 'Numeric'),],
        string="Attribute Type", default='select')


class ProductAttributeLine(models.Model):
    _inherit = "product.attribute.line"

    required = fields.Boolean(
        string='Required', default=True)
    default = fields.Many2one(
        comodel_name='product.attribute.value', string='Default')
    attr_type = fields.Selection(
        string='Attribute Type', store=False,
        related='attribute_id.attr_type')
    
    @api.onchange('attribute_id', 'value_ids')
    def automatic_set_default(self):
        if self.default and self.default.attribute_id == self.attribute_id:
            return
        
        if len(self.value_ids) > 0:
            self.default = self.value_ids[0]
        else:
            self.default = False


class ProductAttributeValue(models.Model):
    _inherit = "product.attribute.value"

    attr_type = fields.Selection(
        string='Attribute Type', related='attribute_id.attr_type')
    numeric_value = fields.Float(
        string='Numeric Value', digits=(12, 6))
    min_range = fields.Float(
        string='Min', digits=(12, 6))
    max_range = fields.Float(
        string='Max', digits=(12, 6))

