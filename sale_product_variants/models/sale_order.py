# -*- encoding: utf-8 -*-
##############################################################################
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see http://www.gnu.org/licenses/.
#
##############################################################################

from openerp import models, fields, api, exceptions, _
from openerp.addons import decimal_precision as dp


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    
    @api.one
    @api.depends('product_attributes')
    def _get_product_attributes_count(self):
        self.product_attributes_count = len(self.product_attributes)

    product_template_id = fields.Many2one(
        comodel_name='product.template', string='Product Template',
        required=True ,readonly=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        domain=[('sale_ok','=',True)])
    product_attributes = fields.Many2many(
        comodel_name='procurement.attribute.line')
    # Neeeded because one2many result type is not constant when evaluating
    # visibility in XML
    product_attributes_count = fields.Integer(
        compute="_get_product_attributes_count")
    order_state = fields.Selection(related='order_id.state')
    product_id = fields.Many2one(
        domain="[('product_tmpl_id', '=', product_template_id)]")
    
    def _get_product_description(self, template, product, product_attributes):
        name = product and product.name or template.name
        group = self.env.ref(
            'sale_product_variants.group_product_variant_extended_description')
        extended = group in self.env.user.groups_id
        if not product_attributes and product:
            product_attributes = [ (0,0, {'attribute': x.attribute_id.id,
                                          'value': x.id,
                                         }) for x in product.attribute_value_ids]
        if extended:
            description = "\n".join(product_attributes.mapped(
                lambda x: "%s: %s" % (x.attribute_id.name, x.name)))
        else:
            description = ", ".join(product_attributes.mapped('name'))
        if not description:
            return name
        return ("%s\n%s" if extended else "%s (%s)") % (name, description)

    @api.multi
    @api.onchange('product_id')
    def product_id_change(self):
        res = super(SaleOrderLine, self).product_id_change()
        if self.product_id:
            product_attributes = self.product_id._get_procurement_attribute_line_dict()
            self.product_attributes = (product_attributes)
            self.name = self._get_product_description(
                self.product_template_id, self.product_id,
                self.product_id.attribute_value_ids)
        return res

    @api.multi
    @api.onchange('product_template_id')
    def onchange_product_template_id(self):
        self.ensure_one()
        if not self.product_template_id:
            self.product_id = False
            self.product_uom = False
            self.price_unit = 0.0
            self.name = ""
            self.product_attributes = False
            self.tax_id = False
        else:
            self.name = self.product_template_id.name
            self.product_id = False
            if not self.product_template_id.attribute_line_ids:
                self.product_id = (
                    self.product_template_id.product_variant_ids and
                    self.product_template_id.product_variant_ids[0])
                self.product_attributes = False
            if not self.product_id:
                self.product_uom = self.product_template_id.uom_id
                product_attributes = self.product_template_id._get_product_tmpl_and_attributes_dict()
                self.product_attributes = (product_attributes)
                self.update_price_unit()
            fpos = self.order_id.fiscal_position_id
            if not fpos:
                fpos = self.order_id.partner_id.property_account_position_id
            self.tax_id = fpos.map_tax(self.product_template_id.taxes_id)

    @api.onchange('product_attributes')
    def onchange_product_attributes(self):
        product_obj = self.env['product.product']
        self.product_id = product_obj._product_find(
            self.product_template_id, self.product_attributes)
        if not self.product_id:
            self.name = self._get_product_description(
                self.product_template_id, False,
                self.product_attributes.mapped('value'))
        if self.product_template_id:
            self.update_price_unit()

    @api.onchange('product_uom', 'product_uom_qty')
    def product_uom_change(self):
        if self.product_id:
            super(SaleOrderLine, self).product_uom_change()
        else:
            if not self.product_uom:
                self.price_unit = 0.0
            else:
                self.update_price_unit()

    @api.multi
    def action_duplicate(self):
        self.ensure_one()
        self.copy()
        # Force reload of the view as a workaround for lp:1155525
        return {
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'sale.order',
            'res_id': self.order_id.id,
            'type': 'ir.actions.act_window',
        }

    @api.one
    def _check_line_confirmability(self):
        if any(not bool(line.value) for line in self.product_attributes):
            raise exceptions.Warning(
                _("(Sale) You can not confirm before configuring all attribute "
                  "values."))

    @api.multi
    def _prepare_order_line_procurement(self, group_id=False):
        self.ensure_one()
        res = super(SaleOrderLine, self)._prepare_order_line_procurement(group_id=group_id)
        res.update({
            'attribute_line_ids':
                    [(4, x.id) for x in self.product_attributes],
        })
        return res

    @api.multi
    def _action_procurement_create(self):
        product_obj = self.env['product.product']
        for line in self:
            if not line.product_id:
                line._check_line_confirmability()
                attr_values = line.product_attributes.mapped('value')
                domain = [('product_tmpl_id', '=', line.product_template_id.id)]
                for attr_value in attr_values:
                    domain.append(('attribute_value_ids', '=', attr_value.id))
                products = product_obj.search(domain)
                # Filter the product with the exact number of attributes values
                product = False
                for prod in products:
                    if len(prod.attribute_value_ids) == len(attr_values):
                        product = prod
                        break
                if not product:
                    product = product_obj.create(
                        {'product_tmpl_id': line.product_template_id.id,
                         'attribute_value_ids': [(6, 0, attr_values.ids)]})
                line.write({'product_id': product.id})
        return super(SaleOrderLine, self)._action_procurement_create()
    
    #Adding 'product_id' to @api.depends forces an update to_invoce_qty on new variant creation
    @api.depends('product_id', 'qty_invoiced', 'qty_delivered', 'product_uom_qty', 'order_id.state')
    def _get_to_invoice_qty(self):
        super(SaleOrderLine, self)._get_to_invoice_qty()
    
    @api.multi
    def update_price_unit(self):
        self.ensure_one()
        if not self.product_id:
            if self.order_id.pricelist_id:
                price_extra = 0.0
                for attr_line in self.product_attributes:
                    #We need this hack to trigger the compute function, otherwise attr_line.price_extra always returns 0.0 here (possible Odoo bug, it seems Odoo does not behave well with a computed variable on NewID 'child' of another NewID)
                    attr_line.value = attr_line.value
                    price_extra += attr_line.price_extra
                self.price_unit = self.order_id.pricelist_id.with_context(
                    {
                        'uom': self.product_uom.id,
                        'date': self.order_id.date_order,
                        'price_extra': price_extra,
                    }).template_price_get(
                    self.product_template_id, self.product_uom_qty or 1.0,
                    self.order_id.partner_id)[self.order_id.pricelist_id.id]
            else:
                self.price_unit = 0
    
    @api.multi
    def get_procurement_lines_as_website_dict(self):
        self.ensure_one()
        
        res = {}
        for line in self.product_attributes:
            res[line.attribute.id] = line.get_attribute_data_dict()
        
        return res

