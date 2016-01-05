# -*- coding: utf-8 -*-
# (c) 2015 Oihane Crucelaegui - AvanzOSC
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from openerp import api, models, fields, _

class ProcurementOrder(models.Model):
    _inherit = 'procurement.order'

    @api.model
    def _prepare_mo_vals(self, procurement):
        result = super(ProcurementOrder, self)._prepare_mo_vals(procurement)
        result['product_template_id'] = procurement.product_id.product_tmpl_id.id
        result['product_attributes'] = [(4, x.id) for x in procurement.attribute_line_ids]
        return result


class StockMove(models.Model):
    _inherit = 'stock.move'
    
    raw_material_prod_line_id = fields.Many2one(
        comodel_name='mrp.production.product.line')
    
    @api.model
    def _prepare_procurement_from_move(self, move):
        res = super(StockMove, self)._prepare_procurement_from_move(move)
        if move.raw_material_prod_line_id:
            res.update({
                'attribute_line_ids' : [(4, x.id) for x in move.raw_material_prod_line_id.product_attributes],
            })
        return res
    
    @api.model
    def _action_explode(self, move):
        if move.procurement_id:
            production_product_attributes = move.procurement_id.attribute_line_ids
        else:
            production_product_attributes = self.env['procurement.attribute.line']
        return super(StockMove, self.with_context(
            production_product_attributes=production_product_attributes))._action_explode(move)

