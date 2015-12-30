from openerp import api, models

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.multi
    def _get_delivered_qty(self):
        return super(SaleOrderLine, self.with_context(
            production_product_attributes=self.product_attributes))._get_delivered_qty()

