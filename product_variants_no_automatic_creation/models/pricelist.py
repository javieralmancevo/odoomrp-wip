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

from openerp import models, fields, tools, api, exceptions, _


class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'

    @api.model
    def _price_rule_get_multi(self, pricelist, products_by_qty_by_partner):
        context = self.env.context.copy() or {} #FIXME I dont see any need for copying the context
        if 'price_extra' not in context and 'product_attribute_values' not in context:
            return super(ProductPricelist, self)._price_rule_get_multi(
                pricelist, products_by_qty_by_partner)
        date = context.get('date') or fields.Date.context_today(self)
        price_extra = context.get('price_extra', 0.0)

        products = map(lambda x: x[0], products_by_qty_by_partner)
        product_uom_obj = self.env['product.uom']
        #price_type_obj = self.env['product.price.type']

        if not products:
            return {}

        #version = False
        #for v in pricelist.version_id:
        #    if (((v.date_start is False) or (v.date_start <= date)) and
        #            ((v.date_end is False) or (v.date_end >= date))):
        #        version = v
        #        break
        #if not version:
        #    raise exceptions.Warning(_("At least one pricelist has no active"
        #                               " version !\nPlease create or activate"
        #                               " one."))
        categ_ids = {}
        for p in products:
            categ = p.categ_id
            while categ:
                categ_ids[categ.id] = True
                categ = categ.parent_id
        categ_ids = categ_ids.keys()

        prod_tmpl_ids = [tmpl.id for tmpl in products]

        # Load all rules
        cr = self.env.cr
        cr.execute(
            'SELECT i.id '
            'FROM product_pricelist_item AS i '
            'WHERE (product_tmpl_id IS NULL OR product_tmpl_id = any(%s)) '
            'AND (product_id IS NULL) ' #TODO check this line
            'AND ((categ_id IS NULL) OR (categ_id = any(%s))) '
            #'AND (price_version_id = %s) '
            #'ORDER BY sequence, min_quantity desc',
            #(prod_tmpl_ids, categ_ids, version.id))
            'AND (pricelist_id = %s) '
            'AND ((i.date_start IS NULL OR i.date_start<=%s) AND (i.date_end IS NULL OR i.date_end>=%s))'
            'ORDER BY applied_on, min_quantity desc',
            (prod_tmpl_ids, categ_ids, pricelist.id, date, date))
        item_ids = [x[0] for x in cr.fetchall()]
        items = self.env['product.pricelist.item'].browse(item_ids)

        price_types = {}
        results = {}
        for product, qty, partner in products_by_qty_by_partner:
            uom_price_already_computed = False
            results[product.id] = 0.0
            price = False
            rule_id = False
            price_uom_id = context.get('uom') or product.uom_id.id
            for rule in items:
                if rule.min_quantity and qty < rule.min_quantity:
                    continue
                if (rule.product_tmpl_id and
                        product.id != rule.product_tmpl_id.id):
                    continue
                if rule.product_id:
                    continue

                #if rule.categ_id:
                #    cat = product.categ_id
                #    while cat:
                #        if cat.id == rule.categ_id.id:
                #            break
                #        cat = cat.parent_id
                #    if not cat:
                #        continue

                #if rule.base == -1:
                #    if rule.base_pricelist_id:
                #        price_tmp = self._price_get_multi(
                #            rule.base_pricelist_id,
                #            [(product, qty, False)])[product.id]
                #        uom_price_already_computed = True
                #        price = pricelist.currency_id.compute(
                #            price_tmp, pricelist.currency_id, round=False)
                #elif rule.base == -2:
                #    for seller in product.seller_ids:
                #        if (not partner) or (seller.name.id != partner):
                #            continue
                #        qty_in_seller_uom = qty
                #        from_uom = context.get('uom') or product.uom_id.id
                #        seller_uom = (seller.product_uom and
                #                      seller.product_uom.id or False)
                #        if seller_uom and from_uom and from_uom != seller_uom:
                #            qty_in_seller_uom = product_uom_obj._compute_qty(
                #                from_uom, qty, to_uom_id=seller_uom)
                #        else:
                #            uom_price_already_computed = True
                #        for line in seller.pricelist_ids:
                #            if line.min_quantity <= qty_in_seller_uom:
                #                price = line.price

                #else:
                #    if rule.base not in price_types:
                #        price_types[rule.base] = price_type_obj.browse(
                #            int(rule.base))
                #    price_type = price_types[rule.base]

                #    uom_price_already_computed = True
                #    price = price_type.currency_id.compute(
                #        product._price_get([product],
                #                           price_type.field)[product.id],
                #        pricelist.currency_id,
                #        round=False)

                if rule.base == 'pricelist' and rule.base_pricelist_id:
                    price_tmp = self._price_get_multi(rule.base_pricelist_id, [(product, qty, partner)])[product.id]
                    ptype_src = rule.base_pricelist_id.currency_id
                    #price = self.pool['res.currency'].compute(cr, uid, ptype_src.id, pricelist.currency_id.id, price_tmp, round=False, context=context)
                    price = ptype_src.compute(price_tmp, pricelist.currency_id, round=False)
                else:
                    # if base option is public price take sale price else cost price of product
                    # price_get returns the price in the context UoM, i.e. qty_uom_id
                    price = self.env['product.template']._price_get([product], rule.base)[product.id]

                if price is not False:
                    price += price_extra
                    #price_limit = price
                    #price = price * (1.0+(rule.price_discount or 0.0))
                    #if rule.price_round:
                    #    price = tools.float_round(
                    #        price, precision_rounding=rule.price_round)
                    #price += (rule.price_surcharge or 0.0)
                    #if rule.price_min_margin:
                    #    price = max(price, price_limit+rule.price_min_margin)
                    #if rule.price_max_margin:
                    #    price = min(price, price_limit+rule.price_max_margin)
                    rule_id = rule.id
                    
                    convert_to_price_uom = (lambda price: product_uom_obj._compute_price(
                                            cr, uid, product.uom_id.id,
                                            price, price_uom_id))
                    
                    if rule.compute_price == 'fixed':
                        price = convert_to_price_uom(rule.fixed_price)
                    elif rule.compute_price == 'percentage':
                        price = (price - (price * (rule.percent_price / 100))) or 0.0
                    else:
                        #complete formula
                        price_limit = price
                        price = (price - (price * (rule.price_discount / 100))) or 0.0
                        if rule.price_round:
                            price = tools.float_round(price, precision_rounding=rule.price_round)

                        if rule.price_surcharge:
                            price_surcharge = convert_to_price_uom(rule.price_surcharge)
                            price += price_surcharge

                        if rule.price_min_margin:
                            price_min_margin = convert_to_price_uom(rule.price_min_margin)
                            price = max(price, price_limit + price_min_margin)

                        if rule.price_max_margin:
                            price_max_margin = convert_to_price_uom(rule.price_max_margin)
                            price = min(price, price_limit + price_max_margin)
                break

            #if price:
            #    if 'uom' in context and not uom_price_already_computed:
            #        uom = product.uos_id or product.uom_id
            #        price = uom._compute_price(price, context['uom'])

            results[product.id] = (price, rule_id)
        return results

    @api.multi
    def template_price_get(self, templ_id, qty, partner_id=None):
        pre_res = self.template_price_rule_get(templ_id, qty, partner_id=partner_id)
        return dict((key, price[0]) for key, price in pre_res.items())

    @api.multi
    def template_price_rule_get(self, templ_id, qty, partner_id=None):
        res_multi = self.price_rule_get_multi(
            products_by_qty_by_partner=[(templ_id, qty, partner_id)])
        res = res_multi[templ_id.id]
        return res

