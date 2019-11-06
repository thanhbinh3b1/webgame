# __author__ = 'BinhTT'

from odoo import models, api, fields
from datetime import datetime
import odoo.addons.decimal_precision as dp


class ESSSaleOrderDiscount(models.Model):
    _inherit = 'sale.order'

    def onchange_partner_id(self, part):
        data = super(ESSSaleOrderDiscount, self).onchange_partner_id(part)
        partner = self.env['res.partner'].browse(part)

        if partner.partner_discount_type != 'none':
            data['value'].update({'ws_discount_type': partner.partner_discount_type})
            if partner.partner_discount_type == 'percent':
                data['value'].update({'ws_discount_percent': partner.partner_discount,
                                      'ws_discount_amount': 0})
            else:
                data['value'].update({'ws_discount_amount': partner.partner_discount,
                                      'ws_discount_percent': 0})
        else:
            data['value'].update({'ws_discount_type': False,
                                  'ws_discount_percent': 0,
                                  'ws_discount_amount': 0})

        return data

    @api.depends('order_line')
    def _compute_all_price(self):
        for r in self:
            r.amount_tax = sum([line.price_tax for line in r.order_line])
            r.amount_untaxed = sum([line.price_subtotal - line.ws_discount for line in r.order_line])
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
                amount_untaxed += line.price_subtotal - line.ws_discount
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

    @api.onchange('item_type')
    def onchange_item_type(self):
        for r in self:
            if r.item_type == 'foc':
                r.price_unit = 0.00

    @api.depends('discount', 'price_unit', 'product_uom_qty')
    def _compute_all_price(self):
        for r in self:
            # r.price_subtotal_discount_line = r.price_unit * r.product_uom_qty * (1 - r.discount / 100)
            r.discount_amount_line = r.price_unit * r.product_uom_qty * r.discount / 100
            # r.price_subtotal = self._calc_line_base_price(r) * r.product_uom_qty - r.ws_discount
            # r.tax_amount = sum([tax['amount'] for tax in r.tax_id.compute_all(r.price_subtotal, 1,
            #                                                                   r.order_id.partner_id)['taxes']])

    @api.depends('ws_discount', 'discount_amount_line')
    def _compute_discount_price(self):
        for r in self:
            r.discount_amount = r.ws_discount + r.discount_amount_line

    # discount = fields.Float(digits=dp.get_precision('Discount'))
    # total_bf_discount = fields.Float(compute="_amount_line_discount",
    #                                  string='Subtotal1', digits_compute=dp.get_precision('Account'))
    # show_discount = fields.Float(digits=(12, 6), string='Discount')

    discount_amount = fields.Float(string='Discount Amount', compute='_compute_discount_price',
                                   store=False, digits=dp.get_precision('Account'))
    discount_amount_line = fields.Float(string='Discount Amount', compute='_compute_all_price',
                                        store=False, digits=dp.get_precision('Account'))
    # price_subtotal = fields.Float(string='Subtotal', compute='_compute_all_price',
    #                               digits=dp.get_precision('Account'),
    #                               help='The Amount after discount on line and whole bill', store=False)
    ws_discount = fields.Float(string='Whole Sale Discount Amount on Line')
    # price_subtotal_discount_line = fields.Float(string='Price Subtotal', digits=dp.get_precision('Account'),
    #                                             compute='_compute_all_price',
    #                                             help="The Amount after discount on line", store=False)
    tax_amount = fields.Float(string='Taxed Amount', digits=dp.get_precision('Account'), compute='_compute_all_price',
                              help='The Tax Amount base on price_subtotal_after_ws_discount', store=False)

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
        return self.price_unit * (1 - (self.discount or 0.0) / 100.0)
    # def _amount_line(self, cr, uid, ids, field_name, arg, context=None):
    #     tax_obj = self.pool.get('account.tax')
    #     cur_obj = self.pool.get('res.currency')
    #     res = {}
    #     if context is None:
    #         context = {}
    #     for line in self.browse(cr, uid, ids, context=context):
    #         price = self._calc_line_base_price(cr, uid, line, context=context)
    #         qty = self._calc_line_quantity(cr, uid, line, context=context)
    #         taxes = tax_obj.compute_all(cr, uid, line.tax_id, price * qty - line.ws_discount, 1,
    #                                     line.product_id,
    #                                     line.order_id.partner_id)
    #         cur = line.order_id.pricelist_id.currency_id
    #         res[line.id] = cur_obj.round(cr, uid, cur, taxes['total'])
    #     return res
    #
    # _columns = {
    #     'price_subtotal': old_fields.function(_amount_line, string='Subtotal',
    #                                           digits_compute=dp.get_precision('Account')),
    # }

    # def _prepare_order_line_proforma_invoice_line(self):
    #     self.ensure_one()
    #     res = super(NpStockPicking, self)._prepare_order_line_proforma_invoice_line()
    #     res.update(ws_discount=self.ws_discount)
    #     return res
    #
    # @api.model
    # def _prepare_order_line_invoice_line(self, line, account_id=False):
    #     res = super(NpStockPicking, self)._prepare_order_line_invoice_line(line, account_id)
    #     res.update(sale_line_id=line.id)
    #     return res


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
