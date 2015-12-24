# -*- encoding: utf-8 -*-

from openerp import models, fields, api, _
from openerp.addons import decimal_precision as dp


class ProcurementAttributeLine(models.Model):
    _name = 'procurement.attribute.line'

    @api.one
    @api.depends('value', 'product_template_id')
    def _get_price_extra(self):
        price_extra = 0.0
        for price in self.value.price_ids:
            if price.product_tmpl_id.id == self.product_template_id.id:
                price_extra = price.price_extra
        self.price_extra = price_extra

    @api.one
    @api.depends('attribute', 'product_template_id',
                 'product_template_id.attribute_line_ids')
    def _get_possible_attribute_values(self):
        attr_values = self.env['product.attribute.value']
        for attr_line in self.product_template_id.attribute_line_ids:
            if attr_line.attribute_id.id == self.attribute.id:
                attr_values |= attr_line.value_ids
        self.possible_values = attr_values.sorted()
    
    product_template_id = fields.Many2one(
        comodel_name='product.template', string='Product')
    attribute = fields.Many2one(
        comodel_name='product.attribute', string='Attribute')
    value = fields.Many2one(
        comodel_name='product.attribute.value', string='Value',
        domain="[('id', 'in', possible_values[0][2])]")
    possible_values = fields.Many2many(
        comodel_name='product.attribute.value',
        compute='_get_possible_attribute_values', readonly=True)
    price_extra = fields.Float(
        compute='_get_price_extra', string='Attribute Price Extra',
        digits=dp.get_precision('Product Price'),
        help="Price Extra: Extra price for the variant with this attribute"
        " value on sale price. eg. 200 price extra, 1000 + 200 = 1200.")
    
    @api.multi
    def get_data_dict(self):
        self.ensure_one()
        return {
            'product_template_id': self.product_template_id.id,
            'attribute': self.attribute.id,
            'value': self.value.id,
        }


class ProcurementOrder(models.Model):
    _inherit = 'procurement.order'
    
    attribute_line_ids = fields.Many2many(
        comodel_name='procurement.attribute.line')


class StockMove(models.Model):
    _inherit = 'stock.move'
    
    @api.model
    def _prepare_procurement_from_move(self, move):
        res = super(StockMove, self)._prepare_procurement_from_move(move)
        if move.procurement_id:
            res.update({
                'attribute_line_ids' : [(4, x.id) for x in move.procurement_id.attribute_line_ids],
            })
        return res

