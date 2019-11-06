# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)

from odoo.exceptions import ValidationError


class sale_global_discount_wizard(models.TransientModel):
    _name = "global_discount.wizard"

    type = fields.Selection([('amount', 'Fixed Amount'), ('percent', 'Percentage')],
                            required=True, default='percent')
    amount = fields.Float('Fixed Amount', required=True)
    percent = fields.Integer('Percentage', required=True)

    def confirm(self):
        self.ensure_one()
        model = self._context.get('active_model')
        order = self.env[model].browse(
            self._context.get('active_id', False))
        if self.env.context.get('active_model') in ('purchase.order', 'sale.order'):
            line_attr = 'order_line'
            if not order.order_line.ids:
                raise ValidationError('You cannot set discount whole bill for order without product')
        elif model == 'account.invoice':
            line_attr = 'invoice_line'
            if not order.invoice_line.ids:
                raise ValidationError('You cannot set discount whole bill for invoice without product')
        else:
            raise ValidationError('You cannot set discount whole bill for %s object' % model)

        discount_amount = 0.0
        if self.type == 'amount':
            discount_amount = self.amount
        if self.type == 'percent':
            if model == 'account.invoice':
                discount_amount = self.percent * sum([line.price_subtotal for line in order.invoice_line]) / 100
            else:
                discount_amount = self.percent * sum([line.price_subtotal for line in order.order_line]) / 100

        vals = {'ws_discount_percent': self.percent,
                'ws_discount_type': self.type}
        if model != 'account.invoice':
            vals.update(ws_discount_amount=discount_amount)

        order.write(vals)

        if model == 'sale.order':
            total_price = sum([line.price_subtotal for line in order.order_line])
        elif model == 'purchase.order':
            total_price = sum([line.price_subtotal for line in order.order_line])
        else:
            total_price = sum([line.price_subtotal for line in order.invoice_line])

        remaining_discount_amount = discount_amount
        line = None
        for line in getattr(order, line_attr):
            try:
                if line.price_unit == 0:
                    line.ws_discount = 0.0
                    continue
            except:
                pass

            line.ws_discount = discount_amount * line.price_subtotal / total_price
            remaining_discount_amount -= line.ws_discount
        line.ws_discount += remaining_discount_amount

        return True

    @api.model
    def recompute_discount(self):
        active_model = self.env.context.get('active_model')
        obj = self.env[active_model].browse(self.env.context.get('active_id'))
        if obj.ws_discount_type:
            wiz = self.create({
                'type': obj.ws_discount_type,
                'amount': obj.ws_discount_amount,
                'percent': obj.ws_discount_percent
            })
            return wiz.confirm()
        else:
            if active_model in ('sale.order', 'purchase.order'):
                obj.order_line.write({'ws_discount': 0})
            if active_model == 'account.invoice':
                obj.invoice_line.write({'ws_discount': 0})
        return True
