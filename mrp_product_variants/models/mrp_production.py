# -*- encoding: utf-8 -*-
##############################################################################
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see http://www.gnu.org/licenses/.
#
##############################################################################

from openerp import models, fields, api, exceptions, _


class MrpProductionAttribute(models.Model):
    _name = 'mrp.production.attribute'

    mrp_production = fields.Many2one(comodel_name='mrp.production',
                                     string='Manufacturing Order')
    attribute = fields.Many2one(comodel_name='product.attribute',
                                string='Attribute')
    value = fields.Many2one(comodel_name='product.attribute.value',
                            domain="[('attribute_id', '=', attribute),"
                            "('id', 'in', possible_values[0][2])]",
                            string='Value')
    possible_values = fields.Many2many(
        comodel_name='product.attribute.value',
        compute='_get_possible_attribute_values')

    @api.one
    @api.depends('attribute', 'mrp_production.product_tmpl_id',
                 'mrp_production.product_tmpl_id.attribute_line_ids')
    def _get_possible_attribute_values(self):
        attr_values = self.env['product.attribute.value']
        template = self.mrp_production.product_tmpl_id
        for attr_line in template.attribute_line_ids:
            if attr_line.attribute_id.id == self.attribute.id:
                attr_values |= attr_line.value_ids
        self.possible_values = attr_values.sorted()


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    product_id = fields.Many2one(
        required=False, string="Variant")
    product_template_id = fields.Many2one(
        comodel_name='product.template', string='Product',
        readonly=True, states={'draft': [('readonly', False)]})
    product_tmpl_id = fields.Many2one(
        related='product_template_id') #TODO test this
    product_attributes = fields.One2many(
        comodel_name='mrp.production.attribute', inverse_name='mrp_production',
        string='Product attributes', copy=True, readonly=True,
        states={'draft': [('readonly', False)]},)

    @api.multi
    def product_id_change(self, product_id, product_qty=0):
        result = super(MrpProduction, self).product_id_change(
            product_id, product_qty=product_qty)
        if 'value' in result:
            if 'bom_id' in result['value'] and not result['value']['bom_id']:
                del result['value']['bom_id']
            if ('routing_id' in result['value'] and
                    not result['value']['routing_id']):
                del result['value']['routing_id']
            if ('product_uom' in result['value'] and
                    not result['value']['product_uom'] and not product_id):
                del result['value']['product_uom']
        if product_id:
            bom_obj = self.env['mrp.bom']
            product = self.env['product.product'].browse(product_id)
            bom_id = bom_obj._bom_find(product_id=product_id, properties=[])
            routing_id = False
            if not bom_id:
                bom_id = bom_obj._bom_find(
                    product_id=product.product_tmpl_id.id, properties=[])
            if bom_id:
                bom_point = bom_obj.browse(bom_id)
                routing_id = bom_point.routing_id.id or False
            result['value'].update(
                {'product_template_id': product.product_tmpl_id.id,
                 'product_attributes': (
                     product._get_product_attributes_values_dict()),
                 'bom_id': bom_id,
                 'routing_id': routing_id})
        else:
            result['value'].update({ #TODO check this, since maybe the right thing is the contrary, keep the template even if the product is gone
                'product_template_id':False
            })
        return result

    @api.multi
    def bom_id_change(self, bom_id):
        res = super(MrpProduction, self).bom_id_change(bom_id)
        if bom_id:
            bom = self.env['mrp.bom'].browse(bom_id)
            if bom.product_id:
                res['value']['product_id'] = bom.product_id.id
            if 'domain' not in res:
                res['domain'] = {}
            res['domain']['routing_id'] = [('id', '=', bom.routing_id.id)]
        return res

    @api.multi
    @api.onchange('product_template_id')
    def onchange_product_template_id(self):
        self.ensure_one()
        if self.product_template_id:
            self.product_uom = self.product_template_id.uom_id
            if (not self.product_template_id.attribute_line_ids and
                    not self.product_id):
                self.product_id = (
                    self.product_template_id.product_variant_ids and
                    self.product_template_id.product_variant_ids[0])
            if not self.product_id:
                self.product_attributes = (
                    self.product_template_id._get_product_attributes_dict())
            else:
                self.product_attributes = (
                    self.product_id._get_product_attributes_values_dict())
            self.bom_id = self.env['mrp.bom']._bom_find(
                product_tmpl_id=self.product_template_id.id)
            self.routing_id = self.bom_id.routing_id
            return {'domain': {'product_id':
                               [('product_tmpl_id', '=',
                                 self.product_template_id.id)],
                               'bom_id':
                               [('product_tmpl_id', '=',
                                 self.product_template_id.id)]}}
        return {'domain': {}}

    @api.one
    @api.onchange('product_attributes')
    def onchange_product_attributes(self):
        product_obj = self.env['product.product']
        self.product_id = product_obj._product_find(self.product_template_id,
                                                    self.product_attributes)

    @api.model
    def _prepare_lines(self, production, properties=None):
        # search BoM structure and route
        bom_obj = self.env['mrp.bom']
        uom_obj = self.env['product.uom']
        bom_point = production.bom_id
        bom_id = production.bom_id.id
        if not bom_point:
            if not production.product_id:
                bom_id = bom_obj._bom_find(
                    product_tmpl_id=production.product_template_id.id,
                    properties=properties)
            else:
                bom_id = bom_obj._bom_find(
                    product_id=production.product_id.id,
                    properties=properties)
            if bom_id:
                bom_point = bom_obj.browse(bom_id)
                routing_id = bom_point.routing_id.id or False
                self.write({'bom_id': bom_id, 'routing_id': routing_id})
        
        if not bom_id:
            raise UserError(_("Cannot find a bill of material for this product."))

        # get components and workcenter_lines from BoM structure
        factor = uom_obj._compute_qty(production.product_uom.id, production.product_qty, to_uom_id=bom_point.product_uom.id)
        # product_lines, workcenter_lines
        return bom_obj._bom_explode(
            bom_point, production.product_id,
            factor / bom_point.product_qty, properties=properties,
            routing_id=production.routing_id.id, production=production)
    
    @api.model
    def _make_production_produce_line(self, production):
        if not production.product_template_id and not production.product_id:
            raise exceptions.Warning(
                _("You can not confirm without product or variant defined."))
        if not production.product_id:
            product_obj = self.env['product.product']
            att_values_ids = [attr_line.value and attr_line.value.id or False
                              for attr_line in production.product_attributes]
            domain = [('product_tmpl_id', '=', production.product_template_id.id)]
            for value in att_values_ids:
                if not value:
                    raise exceptions.Warning(
                        _("You can not confirm before configuring all"
                          " attribute values."))
                domain.append(('attribute_value_ids', '=', value))
            product = product_obj.search(domain)
            if not product:
                product = product_obj.create(
                    {'product_tmpl_id': production.product_template_id.id,
                     'attribute_value_ids': [(6, 0, att_values_ids)]})
            production.product_id = product
        return super(MrpProduction,
                     self)._make_production_produce_line(production)

    @api.model
    def _make_production_consume_line(self, line):
        if not line.product_id:
            product_obj = self.env['product.product']
            att_values_ids = [attr_line.value and attr_line.value.id or False
                              for attr_line in line.product_attributes]
            domain = [('product_tmpl_id', '=', line.product_tmpl_id.id)]
            for value in att_values_ids:
                if not value:
                    raise exceptions.Warning(
                        _("You can not confirm before configuring all"
                          " attribute values."))
                domain.append(('attribute_value_ids', '=', value))
            product = product_obj.search(domain)
            if not product:
                product = product_obj.create(
                    {'product_tmpl_id': line.product_tmpl_id.id,
                     'attribute_value_ids': [(6, 0, att_values_ids)]})
            line.product_id = product
        return super(MrpProduction, self)._make_production_consume_line(line)
    
    @api.multi
    def action_confirm(self):
        """ Confirms production order.
        @return: Newly generated Shipment Id.
        """
        user_lang = self.env.user.partner_id.lang
        #uncompute_ids = filter(lambda x: x, [not x.product_lines and x.id or False for x in self.with_context(lang=user_lang)])
        uncompute_ids = self.with_context(lang=user_lang).filtered(lambda x: not x.product_lines and x.id)
        #self.action_compute(cr, uid, uncompute_ids, context=context)
        uncompute_ids.action_compute()
        for production in self.with_context(lang=user_lang):
            self.with_context(lang=user_lang)._make_production_produce_line(production)
            stock_move_ids = []
            for line in production.product_lines:
                if (line.product_id and line.product_id.type in ['product', 'consu']) or \
                        (line.product_tmpl_id and line.product_tmpl_id.type in ['product', 'consu']):
                    stock_move_id = self.with_context(lang=user_lang)._make_production_consume_line(line)
                    stock_move_ids.append(stock_move_id)
            if stock_move_ids:
                stock_moves = self.env['stock.move'].with_context(lang=user_lang).browse(stock_move_ids)
                stock_moves.action_confirm()
            production.write({'state': 'confirmed'})
        return 0


class MrpProductionProductLineAttribute(models.Model):
    _name = 'mrp.production.product.line.attribute'

    product_line = fields.Many2one(
        comodel_name='mrp.production.product.line',
        string='Product line')
    attribute = fields.Many2one(comodel_name='product.attribute',
                                string='Attribute')
    value = fields.Many2one(comodel_name='product.attribute.value',
                            domain="[('attribute_id', '=', attribute),"
                            "('id', 'in', possible_values[0][2])]",
                            string='Value')
    possible_values = fields.Many2many(
        comodel_name='product.attribute.value',
        compute='_get_possible_attribute_values')

    #@api.one
    #def _get_parent_value(self):
    #    if self.attribute.parent_inherited:
    #        production = self.product_line.production_id
    #        for attr_line in production.product_attributes:
    #            if attr_line.attribute == self.attribute:
    #                self.value = attr_line.value

    @api.one
    @api.depends('attribute')
    def _get_possible_attribute_values(self):
        attr_values = self.env['product.attribute.value']
        template = self.product_line.product_tmpl_id
        for attr_line in template.attribute_line_ids:
            if attr_line.attribute_id.id == self.attribute.id:
                attr_values |= attr_line.value_ids
        self.possible_values = attr_values.sorted()


class MrpProductionProductLine(models.Model):
    _inherit = 'mrp.production.product.line'

    product_id = fields.Many2one(required=False)
    product_tmpl_id = fields.Many2one(comodel_name='product.template',
                                       string='Product')
    product_attributes = fields.One2many(
        comodel_name='mrp.production.product.line.attribute',
        inverse_name='product_line', string='Product attributes',
        copy=True)

    @api.one
    @api.onchange('product_tmpl_id')
    def onchange_product_tmpl_id(self):
        if self.product_tmpl_id:
            product_id = self.env['product.product']
            if not self.product_tmpl_id.attribute_line_ids:
                product_id = (self.product_tmpl_id.product_variant_ids and
                              self.product_tmpl_id.product_variant_ids[0])
                product_attributes = (
                    product_id._get_product_attributes_values_dict())
            else:
                product_attributes = (
                    self.product_tmpl_id._get_product_attributes_inherit_dict(
                        self.production_id.product_attributes))
            self.name = product_id.name or self.product_tmpl_id.name
            self.product_uom = self.product_tmpl_id.uom_id
            self.product_id = product_id
            self.product_attributes = product_attributes

    @api.one
    @api.onchange('product_attributes')
    def onchange_product_attributes(self):
        product_obj = self.env['product.product']
        self.product_id = product_obj._product_find(self.product_tmpl_id,
                                                    self.product_attributes)
