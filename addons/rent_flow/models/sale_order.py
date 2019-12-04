# __author__ = 'BinhTT'
from odoo import fields, api, models, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError, ValidationError


class saleOrder(models.Model):
    _inherit = 'sale.order'

    end_date = fields.Datetime(string='End Date')
    date_rent = fields.Integer('Days', compute='calculate_days')
    cash_detail = fields.One2many('rent.cash', 'sale_id')
    cash_outstanding = fields.Float(string=_('Balance'), compute='total_balance_amount', digits=dp.get_precision('Account'), store=True)
    cash_in = fields.Float(string=_('Cash In'), compute='total_balance_amount', digits=dp.get_precision('Account'), store=True)
    partner_invoice_id = fields.Many2one(required=False)
    partner_shipping_id = fields.Many2one(required=False)

    pricelist_id = fields.Many2one(required=False)
    currency_id = fields.Many2one(related='company_id.currency_id',
                                  required=True)

    @api.depends('order_line')
    def _compute_delivery_state(self):
            self.delivery_set = True

    @api.depends('end_date')
    def calculate_days(self):
        for r in self:
            r.date_rent = 1
            if r.end_date:
                r.date_rent = (self.end_date - self.date_order).days + 1

    @api.depends('cash_detail', 'amount_total')
    def total_balance_amount(self):
        for r in self:
            r.cash_outstanding = r.amount_total
            payment = sum(r.cash_detail.mapped('cash') or [0])
            r.cash_outstanding = r.amount_total - payment
            r.cash_in = sum([r.cash if r.cash > 0 else 0 for r in r.cash_detail] or [0])

    def open_payment(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'rent.cash',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_sale_id': self.id,
                        'from_name': self.name,
                        'from_sale': True},
            'nodestroy': True,
        }

    
    def action_confirm(self):
        if self._get_forbidden_state_confirm() & set(self.mapped('state')):
            raise UserError(_(
                'It is not allowed to confirm an order in the following states: %s'
            ) % (', '.join(self._get_forbidden_state_confirm())))

        for order in self.filtered(lambda order: order.partner_id not in order.message_partner_ids):
            order.message_subscribe([order.partner_id.id])
        self.write({
            'state': 'sale',
        })
        self._action_confirm()
        if self.env.user.has_group('sale.group_auto_done_setting'):
            self.action_done()
        return True