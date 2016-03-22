# -*- coding: utf-8 -*-
# (c) 2015 Oihane Crucelaegui - AvanzOSC
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from openerp import api, models, fields, _

class ProcurementOrder(models.Model):
    _inherit = 'procurement.order'

    @api.model
    def _prepare_mo_vals(self, procurement):
        result = super(ProcurementOrder, self)._prepare_mo_vals(procurement)
        result['product_template_id'] = procurement.product_id.product_tmpl_id.id
        result['product_attributes'] = [(4, x.id) for x in procurement.attribute_line_ids]
        return result


class StockMove(models.Model):
    _inherit = 'stock.move'
    
    raw_material_prod_line_id = fields.Many2one(
        comodel_name='mrp.production.product.line')
    
    @api.model
    def _prepare_procurement_from_move(self, move):
        res = super(StockMove, self)._prepare_procurement_from_move(move)
        if move.raw_material_prod_line_id:
            res.update({
                'attribute_line_ids' : [(4, x.id) for x in move.raw_material_prod_line_id.product_attributes],
            })
        return res
    
    #@api.model
    #def _action_explode(self, move):
    #    if move.procurement_id:
    #        production_product_attributes = move.procurement_id.attribute_line_ids
    #    else:
    #        production_product_attributes = self.env['procurement.attribute.line']
    #    return super(StockMove, self.with_context(
    #        production_product_attributes=production_product_attributes))._action_explode(move)
    
    #All of this is a hack but no other way of doing it for phantom bom
    
    def action_confirm(self, cr, uid, ids, context=None):
        move_ids = []
        proc_attribute_line_dict = {}
        for move in self.browse(cr, uid, ids, context=context):
            #in order to explode a move, we must have a picking_type_id on that move because otherwise the move
            #won't be assigned to a picking and it would be weird to explode a move into several if they aren't
            #all grouped in the same picking.
            if move.picking_type_id:
                new_move_ids, new_proc_attribute_line_dict = self._action_explode_variants(cr, uid, move, context=context)
                move_ids.extend(new_move_ids)
                proc_attribute_line_dict.update(new_proc_attribute_line_dict)
            else:
                move_ids.append(move.id)
        
        if len(proc_attribute_line_dict):
            context_proc_attribute_line_dict = context.get('proc_attribute_line_dict', None)
            if context_proc_attribute_line_dict is None:
                context.update({'proc_attribute_line_dict': proc_attribute_line_dict})
            else:
                context_proc_attribute_line_dict.update(proc_attribute_line_dict)
        
        #we go further with the list of ids potentially changed by action_explode
        return super(StockMove, self).action_confirm(cr, uid, move_ids, context=context)
    
    @api.model
    def _action_explode(self, move):
        return [move.id]
    
    @api.model
    def _action_explode_variants(self, move):
        """ Explodes pickings.
        @param move: Stock moves
        @return: True
        """
        if move.procurement_id:
            production_product_attributes = move.procurement_id.attribute_line_ids
        else:
            production_product_attributes = self.env['procurement.attribute.line']
        
        bom_obj = self.env['mrp.bom']
        move_obj = self.env['stock.move']
        prod_obj = self.env["product.product"]
        proc_obj = self.env["procurement.order"]
        uom_obj = self.env["product.uom"]
        to_explode_again = []
        property_ids = self._context.get('property_ids') or []
        bis = bom_obj.sudo()._bom_find(product_id=move.product_id.id, properties=property_ids) #TODO check
        bom_point = bom_obj.sudo().browse(bis)
        if bis and bom_point.type == 'phantom':
            processed_ids = []
            proc_attribute_line_dict = {}
            
            factor = uom_obj.sudo()._compute_qty(move.product_uom.id, move.product_uom_qty, bom_point.product_uom.id) / bom_point.product_qty
            res = bom_obj.sudo().with_context(production_product_attributes=production_product_attributes). \
                    _bom_explode(bom_point, move.product_id, factor, property_ids)

            for line in res[0]:
                product = prod_obj.browse(line['product_id'])
                if product.type in ['product', 'consu']:
                    valdef = {
                        'picking_id': move.picking_id.id if move.picking_id else False,
                        'product_id': line['product_id'],
                        'product_uom': line['product_uom'],
                        'product_uom_qty': line['product_qty'],
                        'state': 'draft',  #will be confirmed below
                        'name': line['name'],
                        'procurement_id': move.procurement_id.id,
                        'split_from': move.id, #Needed in order to keep sale connection, but will be removed by unlink
                        'price_unit': product.standard_price,
                    }
                    mid = move.copy(default=valdef)
                    to_explode_again.append(mid)
                    proc_attribute_line_dict[mid.id] = line['product_attributes']
                else:
                    if product.type in ('consu','product'): #This will never happen, but it was in the Odoo code so just in case
                        valdef = {
                            'name': move.rule_id and move.rule_id.name or "/",
                            'origin': move.origin,
                            'company_id': move.company_id and move.company_id.id or False,
                            'date_planned': move.date,
                            'product_id': line['product_id'],
                            'product_qty': line['product_qty'],
                            'product_uom': line['product_uom'],
                            'group_id': move.group_id.id,
                            'priority': move.priority,
                            'partner_dest_id': move.partner_id.id,
                            'attribute_line_ids' : line['product_attributes'],
                            }
                        if move.procurement_id:
                            proc = move.procurement_id.copy(default=valdef)
                        else:
                            proc = proc_obj.create(valdef)
                        proc_obj.run([proc]) #could be omitted
            
            #check if new moves needs to be exploded
            if to_explode_again:
                for new_move in to_explode_again:
                    new_move_ids, new_proc_attribute_line_dict = self._action_explode_variants(new_move)
                    processed_ids.extend(new_move_ids)
                    proc_attribute_line_dict.update(new_proc_attribute_line_dict)
            
            if not move.split_from and move.procurement_id:
                # Check if procurements have been made to wait for
                moves = move.procurement_id.move_ids
                if len(moves) == 1:
                    move.procurement_id.write({'state': 'done'})

            if processed_ids and move.state == 'assigned':
                # Set the state of resulting moves according to 'assigned' as the original move is assigned
                result_moves = move_obj.browse(list(set(processed_ids) - set([move.id])))
                result_moves.write({'state': 'assigned'})
                
            #delete the move with original product which is not relevant anymore
            move.sudo().unlink()
            #return list of newly created move
            return processed_ids, proc_attribute_line_dict

        return [move.id], {}

