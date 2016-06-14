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


class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'

    product_id = fields.Many2one(required=False) #TODO domain?
    product_tmpl_id = fields.Many2one(
        comodel_name='product.template', string='Product',
        required=True)
    attribute_value_ids = fields.Many2many(
        domain="[('id', 'in', possible_values[0][2])]",
        string='Values condition', help="BOM Product Values needed to apply this line.")
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
    def get_product_qty(self, production_proc_lines):
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
    
    def _bom_eval_skip_hook(self, attr_line):
        return False
    
    def _skip_bom_line_variants(self, line, product, production_proc_lines):
        """ Control if a BoM line should be produce, can be inherited for add
        custom control.
        @param line: BoM line.
        @param product: Selected product produced.
        @return: True or False
        """
        if line.date_start and \
                (line.date_start > fields.Date.context_today(self))\
                or line.date_stop and \
                (line.date_stop < fields.Date.context_today(self)):
            return True
        
        #Checking the line variants field is satisfied
        if product:
            for limiting_value in line.attribute_value_ids:
                if limiting_value not in product.attribute_value_ids:
                    return True
        
        else:
            for limiting_value in line.attribute_value_ids:
                if not production_proc_lines.filtered(lambda l: l.value == limiting_value):
                    return True
        
        #if line.product_id is not defined, checking that the parent values fit, otherwise skip
        if not line.product_id:
            if product:
                for attr_line in line.product_tmpl_id.attribute_line_ids:
                    if self._bom_eval_skip_hook(attr_line):
                        continue
                    
                    product_value = product.attribute_value_ids.filtered(lambda v: v.attribute_id == attr_line.attribute_id)
                    if not product_value:
                        return True
                    if product_value[0] not in attr_line.value_ids:
                        return True
            
            else:
                for attr_line in line.product_tmpl_id.attribute_line_ids:
                    if self._bom_eval_skip_hook(attr_line):
                        continue
                    attr_proc_line = production_proc_lines.filtered(lambda l: l.attribute == attr_line.attribute_id)
                    if not attr_proc_line:
                        return True
                    if attr_proc_line[0].value not in attr_line.value_ids:
                        return True
        
        return False
    
    @api.multi
    def _get_new_line_dict_from_proc_line(self, template, proc_line, production_proc_lines):
        self.ensure_one()
        
        new_line = proc_line.get_data_dict()
        new_line['product_template_id'] = template.id
        return new_line
    
    @api.multi
    def _get_actualized_product_attributes(self, template, product, product_value_list, production_proc_lines):
        self.ensure_one()
        
        proc_line_dicts = []
        
        values = product.attribute_value_ids if product else product_value_list
        for value in values:
            proc_line = production_proc_lines.filtered(lambda l: l.value == value)
            if proc_line:
                new_line = self._get_new_line_dict_from_proc_line(template, proc_line[0], production_proc_lines)
                
                #if there is a product defined and we need to change the value it can not work
                if product and new_line['value'] != proc_line.value.id:
                    raise exceptions.Warning(_(
                        'The Mrp BoM calculation on attribute {attribute} does not fit in product {product} with value {value}.'
                    ).format(attribute=proc_line.attribute.name, product=product.name, value=value.name))
            else:
                new_line = self.env['procurement.attribute.line'].create_data_dict_from_value(value)
                new_line['product_template_id'] = template.id
                
            proc_line_dicts.append(new_line)
            
        return proc_line_dicts
    
    def _prepare_consume_line_variants(self, bom_line_id, comp_product, quantity, proc_line_dicts):
        return {
            'name': (bom_line_id.product_id.name or
                     bom_line_id.product_tmpl_id.name),
            'product_id': comp_product and comp_product.id or False,
            'product_tmpl_id': (
                bom_line_id.product_tmpl_id.id or
                bom_line_id.product_id.product_tmpl_id.id),
            'product_qty': quantity,
            'product_uom': bom_line_id.product_uom.id,
            'product_attributes': map(lambda x: (0, 0, x), proc_line_dicts),
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
            production_proc_lines = self._context['production_product_attributes']
        else:
            if production:
                production_proc_lines = production.product_attributes
            else:
                raise exceptions.Warning(_('Could not get product_attributes for exploding the BoM.'))
        
        no_create_new_product = self._context.get('bom_explode_no_create_new_product', False)
        
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
            if self._skip_bom_line_variants(bom_line_id, product, production_proc_lines):
                continue
            #TODO properties?
            
            if previous_products and (bom_line_id.product_id.product_tmpl_id.id
                                      in previous_products):
                raise exceptions.Warning(
                    _('Invalid Action! BoM "%s" contains a BoM line with a'
                      ' product recursion: "%s".') %
                    (master_bom.name, bom_line_id.product_id.name_get()[0][1]))

            quantity = _factor(bom_line_id.get_product_qty(production_proc_lines) * factor,
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
                    value_list = bom_line_id.product_tmpl_id._get_inherit_value_list(production_proc_lines, bom)
                    
                    #First we check if we need to change some value given the possible computations (check module mrp_bom_eval)
                    new_proc_line_dicts = bom._get_actualized_product_attributes(
                            bom_line_id.product_tmpl_id, False,
                            value_list, production_proc_lines)
                    
                    comp_product = self.env['product.product']._product_find(
                            bom_line_id.product_tmpl_id, new_proc_line_dicts)
                    comp_product_value_id_list = False
                    
                    if not comp_product:
                        #If the product_product is not in the database we need to check
                        #if the attributes are valid and if so create it.
                        if not bom_line_id.product_tmpl_id.allowed_by_attr_hierarchy_from_dicts(new_proc_line_dicts):
                            raise exceptions.Warning(_('Invalid component attributes combination for BoM component.'))
                        
                        if no_create_new_product:
                            comp_product = False
                            comp_product_value_id_list = [x['value'] for x in new_proc_line_dicts]
                        else:
                            product_values = {
                                'product_tmpl_id': bom_line_id.product_tmpl_id.id,
                                'attribute_value_ids': [(6, 0, [x['value'] for x in new_proc_line_dicts])],
                            }
                            comp_product = self.env['product.product'].with_context(
                                active_test=False,
                                create_product_variant=True
                            ).create(product_values)
                
                else:
                    comp_product = bom_line_id.product_id
                    comp_product_value_id_list = False
                    
                    #_get_actualized_product_attributes will complain if there is a need to change value if product (comp_product) is set
                    new_proc_line_dicts = bom._get_actualized_product_attributes(
                            bom_line_id.product_tmpl_id, comp_product,
                            False, production_proc_lines)
                
                new_result = self._prepare_consume_line_variants(
                    bom_line_id, comp_product,
                    quantity, new_proc_line_dicts)
                
                if no_create_new_product and not comp_product:
                    new_result.update({'product_value_list': comp_product_value_id_list})
                
                result.append(new_result)
            
            elif bom_id:
                all_prod = [bom.product_tmpl_id.id] + (previous_products or [])
                bom2 = self.browse(bom_id)
                # We need to convert to units/UoM of chosen BoM
                factor2 = uom_obj._compute_qty(
                    bom_line_id.product_uom.id, quantity, bom2.product_uom.id)
                quantity2 = factor2 / bom2.get_product_qty(production_proc_lines)
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

