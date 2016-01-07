# -*- coding: utf-8 -*-
# (c) 2015 Serv. Tecnol. Avanzados - Pedro M. Baeza
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from openerp import models, fields, api, _
from openerp.exceptions import Warning as UserError


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.one
    def _check_line_confirmability(self):
        for line in self.product_attributes:
            if line.value:
                continue
            attribute_line = self.product_template.attribute_line_ids.filtered(
                lambda x: x.attribute_id == line.attribute)
            if attribute_line.required:
                raise UserError(
                    _("You cannot confirm before configuring all values "
                      "of required attributes. Product: %s Attribute: %s.") %
                    (self.product_template.name, attribute_line.display_name))

