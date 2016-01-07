# -*- encoding: utf-8 -*-

from openerp import models, fields, api, _


class ProductAttribute(models.Model):
    _inherit = "product.attribute"
    
    #def _attr_type_selection_options(self):
    #    return [
    #        ('select', 'Select'),
    #        ('range', 'Range'),
    #        ('numeric', 'Numeric'),
    #    ]
    
    attr_type = fields.Selection(
        required=True, selection=[
            ('select', 'Select'),
            ('range', 'Range'),
            ('numeric', 'Numeric'),],
        string="Attribute Type", default='select')


class ProductAttributeLine(models.Model):
    _inherit = "product.attribute.line"

    required = fields.Boolean(
        string='Required')
    default = fields.Many2one(
        comodel_name='product.attribute.value', string='Default')
    attr_type = fields.Selection(
        string='Attribute Type', store=False,
        related='attribute_id.attr_type')


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

