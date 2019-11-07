# __author__ = 'BinhTT'
from odoo import fields, api, models


class saleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.onchange('product_id')
    def product_id_change(self):
        res = super(saleOrderLine, self).product_id_change()
        return res

    def _get_display_price(self, product):
        res = super(saleOrderLine, self)._get_display_price(product)
        rent_price = self.env['rent.pricelist'].search([('rent_type', '=', product.rent_type)])
        if rent_price:
            price = rent_price.rent_detail.filtered(lambda x: x.from_day <= self.order_id.date_rent <= x.to_day)
            return max(price.price, rent_price.rent_detail[0].price or 0)
        return res