# -*- coding: utf-8 -*-

from openerp import models, fields, api, _

import logging
_logger = logging.getLogger(__name__)


class ProductAttributeHierarchy (models.Model):
    _name = 'product.attribute.hierarchy'
    
    name = fields.Char(
        string="Name", required=True)
    #parent_attribute_line_ids = fields.One2many(
    #    comodel_name='hierarchy.parent.attribute.line', inverse_name='hierarchy_id',
    #    string="Rules")
    #nodes = fields.One2many(
    #    comodel_name='product.attribute.hierarchy.node', inverse_name='hierarchy_id',
    #    string="Rules")
    rule_line_ids = fields.One2many(
        comodel_name='product.attribute.hierarchy.rule', inverse_name='hierarchy_id',
        string="Rules")
    
    #TODO Right now solved by following attribute sequence. Check circularity. It can be done stablishing a order (that will be used by the webpage and other sale modules to stablish the order to show the attribute options) and making that a parent attribute can not have a child attribute that is higher in the Hierarchy. This will mean that lines with only parent attribute and no child attribute could be created (right now it is not). What about repetition? But once I am designing the webpage module and I am sure about the exact needs I will get back to this.
    
    def allowed_combination(self, attribute_values): #TODO this algo could be greatly improved (probably could be done all in SQL)
        _logger.info("allowed_combination, start, attribute_values: {av}".format(av=attribute_values))
        for value in attribute_values:
            rules_as_parent_attr = self.rule_line_ids.filtered(lambda x: x.parent_attribute_id == value.attribute_id)
            if len(rules_as_parent_attr) > 0:
                rules_as_parent_value = rules_as_parent_attr.filtered(lambda x: value in x.parent_value_ids)
                valid = {}
                for rule in rules_as_parent_value:
                    second_value = attribute_values.filtered(lambda x: x.attribute_id == rule.child_attribute_id)
                    if second_value:
                        if second_value in rule.child_value_ids:
                            valid[rule.child_attribute_id] = True
                        elif not valid.get(rule.child_attribute_id):
                            valid[rule.child_attribute_id] = False
                if not all(valid.values()):
                    return False
        return True


class ProductAttributeHierarchyRule(models.Model):
    _name = 'product.attribute.hierarchy.rule'
    
    #@api.one
    #@api.depends('sequence') #TODO more depends?
    #def _get_allowed_parent_attribute_ids(self):
        #domain = []
        #up_rules = self.search([('sequence', '>', self.sequence)]).sorted(key=lambda x: x.sequence, reverse=True)
        #if up_rules:
            #domain.append(('sequence', '>', up_rules[0].parent_attribute_id.sequence))
        #res = self.env['product.attribute'].search(domain).sorted(key=lambda x: x.sequence)
        #_logger.info("_get_allowed_parent_attribute_ids, res={res}".format(res=res))
        #self.allowed_parent_attribute_ids = res
    
    #def _search_allowed_parent_attribute_ids(self, operator, operand):
    #    _logger.info("search_allowed_parent_attribute_ids, operator:{operator}, operand:{operand}".format(opeartor=operator, operand=operand))
    #    return []
    
    #@api.one
    #@api.depends('parent_attribute_id')
    #def _get_allowed_child_attribute_ids(self):
        #res = self.env['product.attribute'].search([('sequence', '>', self.parent_attribute_id.sequence)]).sorted(key=lambda x: x.sequence)
        #_logger.info("_get_allowed_child_attribute_ids, res={res}".format(res=res))
        #_logger.info("allowed_parent_attribute_ids: {attrs}".format(attrs=self.allowed_parent_attribute_ids))
        #_logger.info("allowed_parent_attribute_ids.mapped('id'): {attrs}".format(attrs=self.allowed_parent_attribute_ids.mapped('id')))
        #_logger.info("allowed_parent_attribute_ids result: {attrs}".format(attrs=(1 in self.allowed_parent_attribute_ids.mapped('id'))))
        #_logger.info("allowed_parent_attribute_ids[0]: {attrs}".format(attrs=self.allowed_parent_attribute_ids[0]))
        #_logger.info("allowed_parent_attribute_ids[0][2]: {attrs}".format(attrs=self.allowed_parent_attribute_ids[0][2]))
        #self.allowed_child_attribute_ids = res
    
    hierarchy_id = fields.Many2one(
        comodel_name='product.attribute.hierarchy', string='Hierarchy')
    sequence = fields.Integer(
        string='Sequence')
    #allowed_parent_attribute_ids = fields.Many2many(
    #    comodel_name='product.attribute', string='Allowed Parent Attributes',
    #    compute='_get_allowed_parent_attribute_ids', readonly=True)
    parent_attribute_id = fields.Many2one(
        comodel_name='product.attribute', string='Parent Attribute',
        required=True)#, domain="[('id', 'in', allowed_parent_attribute_ids)]") #TODO hurhur!
    parent_value_ids = fields.Many2many(
        comodel_name='product.attribute.value', string='Parent Values',
        relation='attribute_hierarchy_rule_parent_values')
        #domain="[('id', 'in', 'parent_attribute_id.value_ids')]") #TODO required?
    #allowed_child_attribute_ids = fields.Many2many(
    #    comodel_name='product.attribute', string='Allowed Child Attributes',
    #    compute='_get_allowed_child_attribute_ids', readonly=True)
    child_attribute_id = fields.Many2one(
        comodel_name='product.attribute', string='Child Attribute',
        required=True)#, domain="[('id', 'in', allowed_child_attribute_ids)]") #TODO hurhur!
    child_value_ids = fields.Many2many(
        comodel_name='product.attribute.value', string='Child Values',
        relation='attribute_hierarchy_rule_child_values')
        #domain="[('id', 'in', 'child_attribute_id.value_ids')]") #TODO required?


"""class ProductAttributeHierarchyNode (models.Model):
    _name = 'product.attribute.hierarchy.node'

    @api.multi
    @api.depends('parent_id', 'parent_id.level')
    def _get_level(self):
        '''Returns a dictionary with key=the ID of a record and value = the level of this  
           record in the tree structure.'''
        for node in self:
            level = 0
            if node.parent_id:
                level = node.parent_id.level + 1
            node.level = level
    
    hierarchy_id = fields.Many2one(
        comodel_name='product.attribute.hierarchy', string='Hierarchy')
    parent_id = fields.Many2one(
        comodel_name='product.attribute.hierarchy.node')
    child_ids = fields.One2many(
        comodel_name='product.attribute.hierarchy.node', inverse_name='parent_id')
    level = fields.Integer(compute='_get_level', string='Level', store=True)
    sequence = fields.Integer('Sequence')
    #type = fields.Selection([
    #    ('parent_attr', 'Parent Attribute Node'),
    #    ('parent_value', 'Parent Value Node'),
    #    ('child', 'Child Node'),
    #    ('account_report', 'Report Value'),
    #    ], 'Type', default='sum')
    parent_attribute_id = fields.Many2one(
        comodel_name='product.attribute', string='Parent Attribute',
        required=True)
    parent_value_ids = fields.Many2many(
        comodel_name='product.attribute.value', string='Parent Values')
    child_attribute_id = fields.Many2one(
        comodel_name='product.attribute', string='Child Attribute',
        required=True)
    child_value_ids = fields.Many2many(
        comodel_name='product.attribute.value', string='Child Values')"""

"""class HierarchyParentAttributeLine (models.Model):
    _name = 'hierarchy.parent.attribute.line'
    
    hierarchy_id = fields.Many2one(
        comodel_name='product.attribute.hierarchy', string='Hierarchy')
    parent_attribute_id = fields.Many2one(
        comodel_name='product.attribute', string='Parent Attribute',
        required=True)
    parent_values_line_ids = fields.One2many(
        comodel_name='hierarchy.parent.value.line', inverse_name='parent_attribute_line',
        string="Parent Value Lines")
    #TODO reference for the order

class HierarchyParentValueLine (models.Model):
    _name = 'hierarchy.parent.value.line'
    
    parent_attribute_line = fields.Many2one(
        comodel_name='hierarchy.parent.attribute.line', string='Parent Attribute')
    parent_attribute_id = fields.Many2one(
        related='parent_attribute_line.parent_attribute_id', store=True)
    parent_value_ids = fields.Many2many(
        comodel_name='product.attribute.value', string='Parent Values')
    child_line_ids = fields.One2many(
        comodel_name='hierarchy.child.line', inverse_name='parent_value_line',
        string="Child Lines", oldname='child_attribute_line_ids')

class HierarchyChildLine (models.Model):
    _name = 'hierarchy.child.line'
    
    parent_value_line = fields.Many2one(
        comodel_name='hierarchy.parent.value.line', string='Parent Value')
    child_attribute_id = fields.Many2one(
        comodel_name='product.attribute', string='Child Attribute',
        required=True)
    child_value_ids = fields.Many2many(
        comodel_name='product.attribute.value', string='Child Values')"""

