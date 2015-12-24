# -*- coding: utf-8 -*-

from openerp import api, models
import logging
_logger = logging.getLogger(__name__)

class ProcurementOrder(models.Model):
    _inherit = 'procurement.order'

    @api.model
    def _prepare_mo_vals(self, procurement):
        result = super(ProcurementOrder, self)._prepare_mo_vals(procurement)
        move = procurement.move_dest_id
        sale_line_id = None
        while(move):
            if move.procurement_id and move.procurement_id.sale_line_id:
                sale_line_id = move.procurement_id.sale_line_id
                break
            move = move.move_dest_id
        if sale_line_id:
            attribute_dict = sale_line_id.get_line_attributes_values_dict()
            _logger.info("the data: {thedata}".format(thedata=attribute_dict))
            result['product_attributes'] = (
                (0, 0, x) for x in attribute_dict)
        _logger.info('return')
        return result

