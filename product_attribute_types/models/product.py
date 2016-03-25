# -*- encoding: utf-8 -*-

from openerp import models, fields, api, exceptions, _


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

    attr_type = fields.Selection(
        string='Attribute Type', store=False,
        related='attribute_id.attr_type')
    
    @api.multi
    def get_value_from_custom_value(self, custom_value):
        self.ensure_one()
        
        if self.attr_type != 'range':
            raise exceptions.Warning('Trying to get the value from custom_value in a non range attribute')
        
        for value in self.value_ids:
            if value.min_range <= custom_value <= value.max_range:
                return value
        return False


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

