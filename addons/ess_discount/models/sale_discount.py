# __author__ = 'BinhTT'

from odoo import models, api, fields
from datetime import datetime
import odoo.addons.decimal_precision as dp


class ESSSaleOrderDiscount(models.Model):
    _inherit = 'sale.order'

    def onchange_partner_id(self):
        data = super(ESSSaleOrderDiscount, self).onchange_partner_id()
        partner = self.partner_id

        if partner.partner_discount_type != 'none':
            self.update({'ws_discount_type': partner.partner_discount_type})
            if partner.partner_discount_type == 'percent':
                self.update({'ws_discount_percent': partner.partner_discount,
                                      'ws_discount_amount': 0})
            else:
                self.update({'ws_discount_amount': partner.partner_discount,
                                      'ws_discount_percent': 0})
        else:
            self.update({'ws_discount_type': False,
                                  'ws_discount_percent': 0,
                                  'ws_discount_amount': 0})

        return data

    @api.depends('order_line')
    def _compute_all_price(self):
        for r in self:
            r.amount_tax = sum([line.price_tax for line in r.order_line])
            r.amount_untaxed = sum([line.price_subtotal - line.ws_discount - line.discount_amount_line for line in r.order_line])
            r.total_before_discount = sum([line.price_subtotal for line in r.order_line])
            r.amount_total = r.amount_untaxed + r.amount_tax
            r.amount_discount = r.total_before_discount - r.amount_untaxed



    @api.depends('order_line.price_total', 'order_line.price_unit', 'order_line.tax_id', 'order_line.discount', 'order_line.product_uom_qty',
                                                       'order_line.ws_discount', 'order_line.price_subtotal')
    def _amount_all(self):
        # TODO: overide to update amount with discount
        """
        Compute the total amounts of the SO.
        """
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.order_line:
                amount_untaxed += line.price_subtotal - line.ws_discount  - line.discount_amount_line
                amount_tax += line.price_tax
            order.update({
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                'amount_total': amount_untaxed + amount_tax,
            })


    total_before_discount = fields.Float(string='Total Amount before Discount',
                                         digits=dp.get_precision('Account'),
                                         compute='_compute_all_price', store=False)

    ws_discount_type = fields.Selection(selection=[('amount', 'Fixed Amount'), ('percent', 'Percentage')],
                                        string='Whole Bill Discount Type', readonly=True)
    ws_discount_amount = fields.Float(string='Whole Bill Discount', digits=dp.get_precision('Account'),
                                      readonly=True)
    ws_discount_percent = fields.Float(string='Whole Bill Discount (%)', digits=dp.get_precision('Discount'),
                                       readonly=True)
    amount_discount = fields.Float(string='Discount Amount', digits=dp.get_precision('Account'),
                                   compute='_compute_all_price', store=False)


    def write(self, vals):
        res = super(ESSSaleOrderDiscount, self).write(vals)
        if self.env.context.get('need_recompute_discount'):
            self.env['global_discount.wizard'].with_context(
                active_ids=self.ids,
                active_id=self.ids[0],
                active_model=self._name,
                need_recompute_discount=False
            ).recompute_discount()
        return res

    @api.model
    def create(self, vals):
        obj = super(ESSSaleOrderDiscount, self).create(vals)
        if obj.ws_discount_type:
            self.env['global_discount.wizard'].with_context(
                active_ids=obj.ids,
                active_id=obj.ids[0],
                active_model=self._name
            ).recompute_discount()
        return obj


class ESSSaleLineDiscount(models.Model):
    _inherit = 'sale.order.line'

    @api.depends('discount', 'price_unit', 'product_uom_qty')
    def _compute_all_price(self):
        for r in self:
            r.discount_amount_line = r.price_unit * r.product_uom_qty * r.discount / 100 + r.discount_amount_manual

    @api.depends('ws_discount', 'discount_amount_line')
    def _compute_discount_price(self):
        for r in self:
            r.discount_amount = r.ws_discount + r.discount_amount_line + r.discount_amount_manual

    discount_type = fields.Selection([('amount', 'By Amount'), ('percent', 'By %')], string='Discount Type')
    discount_amount_manual = fields.Float('Discount $', default=0,
                                          digits=dp.get_precision('Account'))
    discount_amount = fields.Float(string='Discount Amount', compute='_compute_discount_price',
                                   store=False, digits=dp.get_precision('Account'))
    discount_amount_line = fields.Float(string='Discount Amount', compute='_compute_all_price',
                                        store=False, digits=dp.get_precision('Account'))
    ws_discount = fields.Float(string='Whole Sale Discount Amount on Line')
    tax_amount = fields.Float(string='Taxed Amount', digits=dp.get_precision('Account'), compute='_compute_all_price',
                              help='The Tax Amount base on price_subtotal_after_ws_discount', store=False)

    @api.onchange('discount_type')
    def onchange_discount_type(self):
        if self.discount_type == 'amount':
            self.discount = 0
        else:
            self.discount_amount_manual = 0
    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        for line in self:
            price = line._calc_line_base_price()
            qty = line.product_uom_qty
            base_values = round(price * qty - line.ws_discount,line.order_id.currency_id.decimal_places)
            taxes = line.tax_id.with_context(base_values=(base_values,base_values,base_values)).compute_all(
                                            price, line.order_id.currency_id, qty,
                                            product=line.product_id, partner=line.order_id.partner_shipping_id)
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })

    @api.model
    def _calc_line_base_price(self):
        return self.price_unit * (1 - (self.discount or 0.0) / 100.0) - self.discount_amount_manual


class NpPartner(models.Model):
    _inherit = 'res.partner'

    partner_discount_type = fields.Selection(
        selection=[('none', 'Not Applicable'), ('amount', 'Fixed Amount'), ('percent', 'Percentage')],
        string='Whole Bill Discount Type', default='none')
    partner_discount = fields.Float(string='Whole Bill Discount')

    @api.onchange('partner_discount_type')
    def onchange_discount_type(self):
        if self.partner_discount_type == 'none':
            self.partner_discount = 0.00
