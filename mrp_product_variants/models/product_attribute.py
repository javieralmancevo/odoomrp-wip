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

from openerp import api, models, fields, exceptions, _


class ProductAttribute(models.Model):
    _inherit = 'product.attribute'

    parent_inherited = fields.Boolean('Inherits from parent', default=True)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _get_product_attributes_inherit_dict(self, product_attribute_list):
        product_attributes = self._get_product_tmpl_and_attributes_dict()
        for attr in product_attributes:
            if self.env['product.attribute'].browse(
                    attr['attribute']).parent_inherited:
                for attr_line in product_attribute_list:
                    if attr_line.attribute.id == attr['attribute']:
                        attr.update({'value': attr_line.value.id})
        return product_attributes
    
    def _get_inherit_value_hook(self, attr_line, proc_lines, bom):
        return None
    
    @api.multi
    def _get_inherit_value_list(self, proc_lines, bom):
        self.ensure_one()
        
        value_list = []
        for attr_line in self.attribute_line_ids:
            value = self._get_inherit_value_hook(attr_line, proc_lines, bom)
            
            if not value:
                proc_line = proc_lines.filtered(lambda l: l.attribute == attr_line.attribute_id)
                if not proc_line:
                    raise exceptions.Warning(_('Could not find procurement line for attribute.'))
                value = proc_line.value
            
            value_list.append(value)
        
        return value_list

