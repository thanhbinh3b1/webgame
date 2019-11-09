# __author__ = 'BinhTT'
from odoo import fields, api, models, _


class saleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.onchange('product_id')
    def product_id_change(self):
        product = self.product_id.with_context(
            lang=self.order_id.partner_id.lang,
            partner=self.order_id.partner_id,
            quantity=self.product_uom_qty,
            date=self.order_id.date_order,
            pricelist=self.order_id.pricelist_id.id,
            uom=self.product_uom.id
        )
        result = {}
        warning = {}
        if not self.order_id.end_date:
            title = _("Warning for End Date")
            message = 'You should fill in End Date'
            warning['title'] = title
            warning['message'] = message
            result = {'warning': warning}
            return result
        res = super(saleOrderLine, self).product_id_change()

        self.price_unit = self._get_display_price(product)
        return res

    def _get_display_price(self, product):
        # res = super(saleOrderLine, self)._get_display_price(product)
        rent_price = self.env['rent.pricelist'].search([('rent_type', '=', product.rent_type)])
        if rent_price:
            price = rent_price.rent_detail.filtered(lambda x: x.from_day <= self.order_id.date_rent <= x.to_day)
            return max(price.price, rent_price.rent_detail[0].price or 0)
        return product.list_price