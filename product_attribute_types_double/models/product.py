# -*- encoding: utf-8 -*-

from openerp import models, fields, api, _


class ProductAttribute(models.Model):
    _inherit = "product.attribute"
    
    #def _attr_type_selection_options(self):
    #    res = super(ProductAttribute, self)._attr_type_selection_options()
    #    res.append(('double_range', 'Double Range'))
    #    return res
    
    attr_type = fields.Selection(
        required=True, selection=[
            ('select', 'Select'),
            ('range', 'Range'),
            ('numeric', 'Numeric'),
            ('double_range', 'Double Range'),],
        string="Attribute Type", default='select')


class ProductAttributeValue(models.Model):
    _inherit = "product.attribute.value"

    min_range_second = fields.Float(
        string='Second Min', digits=(12, 6))
    max_range_second = fields.Float(
        string='Second Max', digits=(12, 6))

