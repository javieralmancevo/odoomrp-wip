from openerp import models, fields, api, _


class ProcurementOrder(models.Model):
    _inherit = 'procurement.order'
    
    @api.multi
    def _prepare_purchase_order_line(self, po, supplier):
        self.ensure_one()
        
        result = super(ProcurementOrder, self)._prepare_purchase_order_line(po, supplier)
        result['product_template'] = self.product_id.product_tmpl_id.id
        result['product_attributes'] = [(4, x.id) for x in self.attribute_line_ids]
        return result

    @api.multi
    def make_po(self):
        cache = {}
        res = []
        for procurement in self:
            suppliers = procurement.product_id.seller_ids.filtered(lambda r: not r.product_id or r.product_id == procurement.product_id)
            if not suppliers:
                procurement.message_post(body=_('No vendor associated to product %s. Please set one to fix this procurement.') % (procurement.product_id.name))
                continue
            supplier = suppliers[0]
            partner = supplier.name

            gpo = procurement.rule_id.group_propagation_option
            group = (gpo == 'fixed' and procurement.rule_id.group_id) or \
                    (gpo == 'propagate' and procurement.group_id) or False

            domain = (
                ('partner_id', '=', partner.id),
                ('state', '=', 'draft'),
                ('picking_type_id', '=', procurement.rule_id.picking_type_id.id),
                ('company_id', '=', procurement.company_id.id),
                ('dest_address_id', '=', procurement.partner_dest_id.id))
            if group:
                domain += (('group_id', '=', group.id),)

            if domain in cache:
                po = cache[domain]
            else:
                po = self.env['purchase.order'].search([dom for dom in domain])
                po = po[0] if po else False
                cache[domain] = po
            if not po:
                vals = procurement._prepare_purchase_order(partner)
                po = self.env['purchase.order'].create(vals)
                cache[domain] = po
            elif not po.origin or procurement.origin not in po.origin.split(', '):
                # Keep track of all procurements
                if po.origin:
                    po.write({'origin': po.origin + ', ' + procurement.origin})
                else:
                    po.write({'origin': procurement.origin})
            res += po.ids

            # Create Line
            po_line = False
            for line in po.order_line:
                #this is the only part that changes, it would be good if Odoo could include it as a hook
                if line.products_are_compatible(procurement):
                    seller = self.product_id._select_seller(
                        self.product_id,
                        partner_id=partner,
                        quantity=line.product_qty + procurement.product_qty,
                        date=po.date_order and po.date_order[:10],
                        uom_id=self.product_uom)

                    price_unit = self.env['account.tax']._fix_tax_included_price(seller.price, line.product_id.supplier_taxes_id, line.taxes_id) if seller else 0.0
                    if price_unit and seller and po.currency_id and seller.currency_id != po.currency_id:
                        price_unit = seller.currency_id.compute(price_unit, po.currency_id)

                    if seller and self.product_uom and seller.product_uom != self.product_uom:
                        price_unit = self.env['product.uom']._compute_price(seller.product_uom.id, price_unit, to_uom_id=self.product_uom.id)

                    po_line = line.write({
                        'product_qty': line.product_qty + procurement.product_qty,
                        'price_unit': price_unit,
                        'procurement_ids': [(4, procurement.id)]
                    })
                    break
            if not po_line:
                vals = procurement._prepare_purchase_order_line(po, supplier)
                self.env['purchase.order.line'].create(vals)
        return res

