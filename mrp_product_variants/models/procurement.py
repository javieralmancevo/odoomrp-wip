# -*- coding: utf-8 -*-
# (c) 2015 Oihane Crucelaegui - AvanzOSC
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from openerp import api, models

class ProcurementOrder(models.Model):
    _inherit = 'procurement.order'

    @api.model
    def _prepare_mo_vals(self, procurement):
        result = super(ProcurementOrder, self)._prepare_mo_vals(procurement)
        product_id = result.get('product_id')
        product = self.env['product.product'].browse(product_id)
        result['product_template_id'] = product.product_tmpl_id.id
        result['product_attributes'] = [(4, x.id) for x in procurement.attribute_line_ids]
        return result

class StockMove(models.Model):
    _inherit = 'stock.move'
    
    @api.model
    def _action_explode(self, move):
        if move.procurement_id:
            production_product_attributes = move.procurement_id.attribute_line_ids
        else:
            production_product_attributes = self.env['procurement.attribute.line']
        return super(StockMove, self.with_context(
            production_product_attributes=production_product_attributes))._action_explode(move)

