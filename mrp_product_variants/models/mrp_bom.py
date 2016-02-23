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

from openerp import models, fields, api, exceptions, tools, _
from openerp import tools
from itertools import groupby
from operator import attrgetter


class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'

    product_id = fields.Many2one(required=False) #TODO domain?
    product_tmpl_id = fields.Many2one(
        comodel_name='product.template', string='Product',
        required=True)
    attribute_value_ids = fields.Many2many(
        domain="[('id', 'in', possible_values[0][2])]")
    possible_values = fields.Many2many(
        comodel_name='product.attribute.value',
        compute='_get_possible_attribute_values')

    @api.one
    @api.depends('product_id', 'product_tmpl_id')
    def _get_product_category(self):
        self.product_uom_category = (self.product_id.uom_id.category_id or
                                     self.product_tmpl_id.uom_id.category_id)

    product_uom_category = fields.Many2one(
        comodel_name='product.uom.categ', string='UoM category',
        compute="_get_product_category")
    product_uom = fields.Many2one(
        domain="[('category_id', '=', product_uom_category)]")

    @api.one
    @api.depends('bom_id.product_tmpl_id',
                 'bom_id.product_tmpl_id.attribute_line_ids')
    def _get_possible_attribute_values(self):
        attr_values = self.env['product.attribute.value']
        for attr_line in self.bom_id.product_tmpl_id.attribute_line_ids:
            attr_values |= attr_line.value_ids
        self.possible_values = attr_values.sorted()

    @api.multi
    def onchange_product_id(self, product_id, product_qty=0):
        res = super(MrpBomLine, self).onchange_product_id(
            product_id, product_qty=product_qty)
        if product_id:
            product = self.env['product.product'].browse(product_id)
            res['value']['product_tmpl_id'] = product.product_tmpl_id.id
        return res

    @api.multi
    @api.onchange('product_tmpl_id')
    def onchange_product_tmpl_id(self):
        if self.product_tmpl_id:
            self.product_uom = (self.product_id.uom_id or
                                self.product_tmpl_id.uom_id)
            return {'domain': {'product_id': [('product_tmpl_id', '=',
                                               self.product_tmpl_id.id)]}}
        return {'domain': {'product_id': []}}
    
    @api.multi
    def get_product_qty(self, production_product_attributes):
        self.ensure_one()
        return self.product_qty


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    @api.model
    def _bom_explode(self, bom, product, factor, properties=None, level=0,
                     routing_id=False, previous_products=None,
                     master_bom=None, production=None):
        result, result2 = self._bom_explode_variants(
            bom, product, factor, properties=properties, level=level,
            routing_id=routing_id, previous_products=previous_products,
            master_bom=master_bom, production=production)
        return result, result2

    def _check_product_suitable(self, check_attribs, component_attribs):
        """ Check if component is suitable for given attributes
        @param check_attribs: Attribute id list
        @param component_attribs: Component defined attributes to check
        @return: Component validity
        """
        getattr = attrgetter('attribute_id')
        for key, group in groupby(component_attribs, getattr):
            if not set(check_attribs).intersection([x.id for x in group]):
                return False
        return True
    
    def _skip_bom_line_variants(self, line_id, product_id, production_id):
        """ Control if a BoM line should be produce, can be inherited for add
        custom control.
        @param line: BoM line.
        @param product: Selected product produced.
        @return: True or False
        """
        if line_id.date_start and \
                (line_id.date_start > fields.Date.context_today(self))\
                or line_id.date_stop and \
                (line_id.date_stop < fields.Date.context_today(self)):
            return True        # all bom_line_id variant values must be in the product
        if line_id.attribute_value_ids:
            production_attr_values = []
            if not product_id and production_id:
                for attr_value in production_id.product_attributes:
                    production_attr_values.append(attr_value.value.id)
                if not self._check_product_suitable(
                        production_attr_values,
                        line_id.attribute_value_ids):
                    return True
            elif not product_id or not self._check_product_suitable(
                    product_id.attribute_value_ids.ids,
                    line_id.attribute_value_ids):
                return True
        return False
    
    def _get_actualized_product_attributes(self, product_id, production_product_attributes):
        product_attributes_dict_list = []
        for attr_value in product_id.attribute_value_ids:
            new_line = None
            for attr_line in production_product_attributes:
                if attr_value == attr_line.value:
                    new_line = attr_line.get_data_dict()
                    new_line['product_template_id'] = \
                        product_id.product_tmpl_id.id
                    break
            if not new_line:
                new_line = {
                    'value': attr_value.id,
                    'attribute': attr_value.attribute_id.id,
                    'product_template_id': product_id.product_tmpl_id.id,
                }
            product_attributes_dict_list.append(new_line)
        return product_attributes_dict_list
    
    def _prepare_consume_line_variants(self, bom_line_id, comp_product, quantity, product_attributes):
        return {
            'name': (bom_line_id.product_id.name or
                     bom_line_id.product_tmpl_id.name),
            'product_id': comp_product and comp_product.id,
            'product_tmpl_id': (
                bom_line_id.product_tmpl_id.id or
                bom_line_id.product_id.product_tmpl_id.id),
            'product_qty': quantity,
            'product_uom': bom_line_id.product_uom.id,
            'product_attributes': map(lambda x: (0, 0, x), product_attributes),
        }
    
    @api.model
    def _bom_explode_variants(
            self, bom, product, factor, properties=None, level=0,
            routing_id=False, previous_products=None, master_bom=None,
            production=None):
        """ Finds Products and Work Centers for related BoM for manufacturing
        order.
        @param bom: BoM of particular product template.
        @param product: Select a particular variant of the BoM. If False use
                        BoM without variants.
        @param factor: Factor represents the quantity, but in UoM of the BoM,
                        taking into account the numbers produced by the BoM
        @param properties: A List of properties Ids.
        @param level: Depth level to find BoM lines starts from 10.
        @param previous_products: List of product previously use by bom explore
                        to avoid recursion
        @param master_bom: When recursion, used to display the name of the
                        master bom
        @return: result: List of dictionaries containing product details.
                 result2: List of dictionaries containing Work Center details.
        """
        routing_id = bom.routing_id.id or routing_id
        uom_obj = self.env["product.uom"]
        routing_obj = self.env['mrp.routing']
        master_bom = master_bom or bom
        
        if 'production_product_attributes' in self._context:
            production_product_attributes = self._context['production_product_attributes']
        else:
            if production:
                production_product_attributes = production.product_attributes
            else:
                raise exceptions.Warning(_('Could not get product_attributes for exploding the BoM.'))

        def _factor(factor, product_efficiency, product_rounding):
            factor = factor / (product_efficiency or 1.0)
            if product_rounding:
                factor = tools.float_round(factor,
                                           precision_rounding=product_rounding,
                                           rounding_method='UP')
            if factor < product_rounding:
                factor = product_rounding
            return factor

        factor = _factor(factor, bom.product_efficiency, bom.product_rounding)

        result = []
        result2 = []

        routing = (routing_id and routing_obj.browse(cr, uid, routing_id)) or bom.routing_id or False
        if routing:
            for wc_use in routing.workcenter_lines:
                result2.append(self._prepare_wc_line(
                    cr, uid, bom, wc_use, level=level, factor=factor,
                    context=context))
        
        for bom_line_id in bom.bom_line_ids:
            if self._skip_bom_line_variants(bom_line_id, product, production):
                continue
            #TODO properties?
            
            if previous_products and (bom_line_id.product_id.product_tmpl_id.id
                                      in previous_products):
                raise exceptions.Warning(
                    _('Invalid Action! BoM "%s" contains a BoM line with a'
                      ' product recursion: "%s".') %
                    (master_bom.name, bom_line_id.product_id.name_get()[0][1]))

            quantity = _factor(bom_line_id.get_product_qty(production_product_attributes) * factor,
                               bom_line_id.product_efficiency,
                               bom_line_id.product_rounding)
            bom_id = False
            if bom_line_id.product_id:
                bom_id = self._bom_find(product_id=bom_line_id.product_id.id,
                                        properties=properties)

            #  If BoM should not behave like PhantoM, just add the product,
            #  otherwise explode further
            if not bom_id or self.browse(bom_id).type != "phantom":
                if not bom_line_id.product_id:
                    product_attributes_dicts = (
                        bom_line_id.product_tmpl_id.
                        _get_product_attributes_inherit_dict(
                            production_product_attributes))
                    comp_product = self.env['product.product']._product_find(
                        bom_line_id.product_tmpl_id, product_attributes_dicts)
                    
                    if not comp_product:
                        #If the product_product is not in the database we need to check
                        #if the attributes are valid and if so create it.
                        if not bom_line_id.product_tmpl_id.allowed_by_attr_hierarchy_from_dicts(product_attributes_dicts):
                            raise exceptions.Warning(_('Invalid component attributes combination.'))
                        
                        product_values = {
                            'product_tmpl_id': bom_line_id.product_tmpl_id.id,
                            'attribute_value_ids': [(6, 0, [x['value'] for x in product_attributes_dicts])],
                            #map(lambda x: (6, 0, x['value']), product_attributes_dicts),
                        }
                        comp_product = self.env['product_product'].with_context(
                            active_test=False,
                            create_product_variant=True
                        ).create(product_values)
                
                else:
                    comp_product = bom_line_id.product_id
                
                product_attributes = self._get_actualized_product_attributes(
                    comp_product, production_product_attributes)
                result.append(self._prepare_consume_line_variants(
                    bom_line_id, comp_product,
                    quantity, product_attributes))
            
            elif bom_id:
                all_prod = [bom.product_tmpl_id.id] + (previous_products or [])
                bom2 = self.browse(bom_id)
                # We need to convert to units/UoM of chosen BoM
                factor2 = uom_obj._compute_qty(
                    bom_line_id.product_uom.id, quantity, bom2.product_uom.id)
                quantity2 = factor2 / bom2.get_product_qty(production_product_attributes)
                res = self._bom_explode(
                    bom2, bom_line_id.product_id, quantity2,
                    properties=properties, level=level + 10,
                    previous_products=all_prod, master_bom=master_bom,
                    production=production)
                result = result + res[0]
                result2 = result2 + res[1]
            else:
                if not bom_line_id.product_id:
                    name = bom_line_id.product_tmpl_id.name_get()[0][1]
                else:
                    name = bom_line_id.product_id.name_get()[0][1]
                raise exceptions.Warning(
                    _('Invalid Action! BoM "%s" contains a phantom BoM line'
                      ' but the product "%s" does not have any BoM defined.') %
                    (master_bom.name, name))
        return result, result2

