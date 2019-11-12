# __author__ = 'BinhTT'
from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError


class ChooseDeliveryCarrier(models.TransientModel):
    _inherit = 'choose.delivery.carrier'

    purchase_id = fields.Many2one('purchase.order', ondelete="cascade")
    order_id = fields.Many2one(required=False)

    def button_confirm(self):
        if self._context.get('default_purchase_id', False):
            self.purchase_id.set_delivery_line(self.carrier_id, self.delivery_price)
            self.purchase_id.write({
                'recompute_delivery_price': False,
                'delivery_message': self.delivery_message,
                'carrier_id': self.carrier_id.id
            })
            return
        super(ChooseDeliveryCarrier, self).button_confirm()

    def _get_shipment_rate(self):
        if self._context.get('default_purchase_id', False):
            vals = self.carrier_id.rate_shipment(self.purchase_id)
            if vals.get('success'):
                self.delivery_message = vals.get('warning_message', False)
                self.delivery_price = vals['price']
                self.display_price = vals['carrier_price']
                return {}
        super(ChooseDeliveryCarrier, self)._get_shipment_rate()


class RentDeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    def fixed_rate_shipment(self, order):
        carrier = self._match_address(order.partner_id)
        if not carrier:
            return {'success': False,
                    'price': 0.0,
                    'error_message': _('Error: this delivery method is not available for this address.'),
                    'warning_message': False}
        price = self.fixed_price
        if self.company_id and self.company_id.currency_id.id != order.currency_id.id:
            price = self.company_id.currency_id._convert(price, order.currency_id, self.company_id, fields.Date.today())
        return {'success': True,
                'price': price,
                'error_message': False,
                'warning_message': False}

    def base_on_rule_rate_shipment(self, order):
        carrier = self._match_address(order.partner_id)
        if not carrier:
            return {'success': False,
                    'price': 0.0,
                    'error_message': _('Error: this delivery method is not available for this address.'),
                    'warning_message': False}

        try:
            price_unit = self._get_price_available(order)
        except UserError as e:
            return {'success': False,
                    'price': 0.0,
                    'error_message': e.name,
                    'warning_message': False}
        # if order.company_id.currency_id.id != order.pricelist_id.currency_id.id:
        #     price_unit = order.company_id.currency_id._convert(
        #         price_unit, order.pricelist_id.currency_id, order.company_id, order.date_order or fields.Date.today())

        return {'success': True,
                'price': price_unit,
                'error_message': False,
                'warning_message': False}