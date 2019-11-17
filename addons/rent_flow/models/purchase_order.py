# __author__ = 'BinhTT'
from odoo import fields, api, models, _
import odoo.addons.decimal_precision as dp


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    carrier_id = fields.Many2one('delivery.carrier', string="Delivery Method",
                                 domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
                                 help="Fill this field if you plan to invoice the shipping based on picking.")
    delivery_message = fields.Char(readonly=True, copy=False)
    delivery_rating_success = fields.Boolean(copy=False)
    delivery_set = fields.Boolean(compute='_compute_delivery_state')
    recompute_delivery_price = fields.Boolean('Delivery cost should be recomputed')
    cash_detail = fields.One2many('rent.cash', 'purchase_id')
    cash_outstanding = fields.Float(string=_('Balance'), compute='total_balance_amount', digits=dp.get_precision('Account'), store=True)


    @api.depends('cash_detail', 'amount_total')
    def total_balance_amount(self):
        for r in self:
            r.cash_outstanding = r.amount_total
            payment = sum(r.cash_detail.mapped('cash') or [0])
            r.cash_outstanding = r.amount_total + payment

    @api.depends('order_line')
    def _compute_delivery_state(self):
        delivery_line = self.order_line.filtered('is_delivery')
        if delivery_line:
            self.delivery_set = True
        else:
            self.delivery_set = False

    @api.onchange('order_line', 'partner_id')
    def onchange_order_line(self):
        delivery_line = self.order_line.filtered('is_delivery')
        if delivery_line:
            self.recompute_delivery_price = True

    def _remove_delivery_line(self):
        self.env['purchase.order.line'].search([('order_id', 'in', self.ids), ('is_delivery', '=', True)]).unlink()

    def set_delivery_line(self, carrier, amount):

        # Remove delivery products from the purchases order
        self._remove_delivery_line()

        for order in self:
            order._create_delivery_line(carrier, amount)
        return True

    def action_open_delivery_wizard(self):
        view_id = self.env.ref('delivery.choose_delivery_carrier_view_form').id
        if self.env.context.get('carrier_recompute'):
            name = _('Update shipping cost')
            carrier = self.carrier_id
        else:
            name = _('Add a shipping method')
            carrier = self.partner_id.property_delivery_carrier_id
        return {
            'name': name,
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'choose.delivery.carrier',
            'view_id': view_id,
            'views': [(view_id, 'form')],
            'target': 'new',
            'context': {
                'default_purchase_id': self.id,
                'default_carrier_id': carrier.id,
            }
        }

    def _create_delivery_line(self, carrier, price_unit):
        PurchaseOrderLine = self.env['purchase.order.line']
        if self.partner_id:
            # set delivery detail in the customer language
            carrier = carrier.with_context(lang=self.partner_id.lang)

        # Apply fiscal position
        taxes = carrier.product_id.taxes_id.filtered(lambda t: t.company_id.id == self.company_id.id)
        taxes_ids = taxes.ids
        if self.partner_id and self.fiscal_position_id:
            taxes_ids = self.fiscal_position_id.map_tax(taxes, carrier.product_id, self.partner_id).ids

        # Create the purchases order line
        carrier_with_partner_lang = carrier.with_context(lang=self.partner_id.lang)
        if carrier_with_partner_lang.product_id.description_sale:
            so_description = '%s: %s' % (carrier_with_partner_lang.name,
                                         carrier_with_partner_lang.product_id.description_sale)
        else:
            so_description = carrier_with_partner_lang.name
        values = {
            'order_id': self.id,
            'name': so_description,
            'product_qty': 1,
            'product_uom_qty': 1,
            'product_uom': carrier.product_id.uom_id.id,
            'product_id': carrier.product_id.id,
            'is_delivery': True,
            'date_planned': self.date_order,
        }
        if carrier.invoice_policy == 'real':
            values['price_unit'] = 0
            values['name'] += _(' (Estimated Cost: %s )') % self._format_currency_amount(price_unit)
        else:
            values['price_unit'] = price_unit
        if carrier.free_over and self.currency_id.is_zero(price_unit):
            values['name'] += '\n' + 'Free Shipping'
        if self.order_line:
            values['sequence'] = self.order_line[-1].sequence + 1
        sol = PurchaseOrderLine.sudo().create(values)
        return sol

    def _format_currency_amount(self, amount):
        pre = post = u''
        if self.currency_id.position == 'before':
            pre = u'{symbol}\N{NO-BREAK SPACE}'.format(symbol=self.currency_id.symbol or '')
        else:
            post = u'\N{NO-BREAK SPACE}{symbol}'.format(symbol=self.currency_id.symbol or '')
        return u' {pre}{0}{post}'.format(amount, pre=pre, post=post)

    def open_payment(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'rent.cash',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_purchase_id': self.id,
                        'from_name': self.name,
                        'default_cash_type': 'out',
                        'from_sale': True},
            'nodestroy': True,
        }


class purchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    is_delivery = fields.Boolean(string="Is a Delivery", default=False)
    recompute_delivery_price = fields.Boolean(related='order_id.recompute_delivery_price')

    def unlink(self):
        for line in self:
            if line.is_delivery:
                line.order_id.carrier_id = False
        super(purchaseOrderLine, self).unlink()

    def _is_delivery(self):
        self.ensure_one()
        return self.is_delivery

    # override to allow deletion of delivery line in a confirmed order
    def _check_line_unlink(self):
        """
        Extend the allowed deletion policy of SO lines.

        Lines that are delivery lines can be deleted from a confirmed order.

        :rtype: recordset purchase.order.line
        :returns: set of lines that cannot be deleted
        """

        undeletable_lines = super()._check_line_unlink()
        return undeletable_lines.filtered(lambda line: not line.is_delivery)