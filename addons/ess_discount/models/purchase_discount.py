# __author__ = 'BinhTT'

from odoo import models, fields, api
# from openerp.osv import fields as old_fields
import odoo.addons.decimal_precision as dp


class EssPurchaseDiscount(models.Model):
    _inherit = 'purchase.order'

    @api.depends('order_line')
    def _compute_all_price(self):
        for r in self:

            r.amount_tax = sum([line.price_tax for line in r.order_line])
            r.amount_untaxed = sum([line.price_subtotal - line.ws_discount for line in r.order_line])
            r.discount_amount = sum([line.ws_discount  for line in r.order_line])
            r.total_before_discount = sum([line.price_subtotal for line in r.order_line])
            r.amount_total = r.amount_untaxed + r.amount_tax



    total_before_discount = fields.Float(string='Total Amount before Discount',
                                         digits=dp.get_precision('Account'),
                                         compute='_compute_all_price', store=True)

    ws_discount_type = fields.Selection(selection=[('amount', 'Fixed Amount'), ('percent', 'Percentage')],
                                        string='Whole Bill Discount Type', readonly=True)
    ws_discount_amount = fields.Float(string='Whole Bill Discount', digits=dp.get_precision('Account'),
                                      readonly=True)
    ws_discount_percent = fields.Float(string='Whole Bill Discount (%)', digits=dp.get_precision('Discount'),
                                       readonly=True)

    discount_amount = fields.Float(compute='_compute_all_price')
    amount_untaxed = fields.Float(compute='_compute_all_price')
    amount_tax = fields.Float(compute='_compute_all_price')
    amount_total = fields.Float(compute='_compute_all_price')

    def write(self, vals):
        res = super(EssPurchaseDiscount, self).write(vals)
        if self.env.context.get('need_recompute_discount') and self:
            self.env['global_discount.wizard'].with_context(
                active_ids=self.ids,
                active_id=self.ids[0],
                active_model=self._name,
                need_recompute_discount=False
            ).recompute_discount()
        return res

    @api.model
    def create(self, vals):
        obj = super(EssPurchaseDiscount, self).create(vals)
        if obj.ws_discount_type:
            self.env['global_discount.wizard'].with_context(
                active_ids=obj.ids,
                active_id=obj.ids[0],
                active_model=self._name
            ).recompute_discount()
        return obj


class NpPurchaseLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.depends('discount', 'price_unit', 'product_qty')
    def _compute_all_price(self):
        for r in self:
            r.discount_amount_line = r.price_unit * r.product_qty * r.discount / 100

    @api.depends('ws_discount', 'discount_amount_line')
    def _compute_discount_price(self):
        for r in self:
            r.discount_amount = r.ws_discount + r.discount_amount_line

    @api.depends('price_unit', 'ws_discount', 'discount', 'product_qty')
    def _compute_final_price_unit(self):
        for r in self:
            r.final_price_unit = (r.price_unit * r.product_qty * (1 - r.discount / 100) - r.ws_discount) /r.product_qty

    discount = fields.Float(string='Discount (%)', igits=dp.get_precision('Discount'),
                            readonly=True, states={'draft': [('readonly', False)]})

    discount_amount = fields.Float(string='Discount Amount', compute='_compute_discount_price',
                                   store=False, digits=dp.get_precision('Account'))
    discount_amount_line = fields.Float(string='Discount Amount', compute='_compute_all_price',
                                        store=False, digits=dp.get_precision('Account'))
    ws_discount = fields.Float(string='Whole Sale Discount Amount on Line')

    tax_amount = fields.Float(string='Taxed Amount', digits=dp.get_precision('Account'), compute='_compute_all_price',
                              help='The Tax Amount base on price_subtotal_after_ws_discount', store=False)
    final_price_unit = fields.Float(string='Price Unit', digits=dp.get_precision('Product Price'),
                                    compute='_compute_final_price_unit')

    @api.depends('product_qty', 'price_unit', 'taxes_id', 'discount')
    def _compute_amount(self):
        # TODO: overide and compute with new price_unit with discount
        for line in self:
            vals = line._prepare_compute_all_values()
            line_price = line._calc_line_base_price()
            taxes = line.taxes_id.compute_all(
                line_price,
                vals['currency_id'],
                vals['product_qty'],
                vals['product'],
                vals['partner'])
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })

    @api.model
    def _calc_line_base_price(self):
        """Return the base price of the line to be used for tax calculation.

        This function can be extended by other modules to modify this base
        price (adding a discount, for example).
        """
        return self.price_unit * (1 - (self.discount or 0.0) / 100.0)

