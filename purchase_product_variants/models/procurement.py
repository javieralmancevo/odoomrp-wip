from openerp import models, fields, api, _


class ProcurementOrder(models.Model):
    _inherit = 'procurement.order'
    
    @api.multi
    def _prepare_purchase_order_line(self, po, supplier):
        self.ensure_one()
        
        result = super(ProcurementOrder, self)._prepare_purchase_order_line(po, supplier)
        product_id = result.get('product_id')
        product = self.env['product.product'].browse(product_id)
        result['product_template_id'] = product.product_tmpl_id.id
        result['product_attributes'] = [(4, x.id) for x in procurement.attribute_line_ids]
        return result
    
    #TODO
    #@api.multi
    #def make_po(self):

