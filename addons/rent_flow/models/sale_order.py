# __author__ = 'BinhTT'
from odoo import fields, api, models, _


class saleOrder(models.Model):
    _inherit = 'sale.order'

    end_date = fields.Date(string='End Date')
    date_rent = fields.Integer('Days', compute='calculate_days')
    cash_detail = fields.One2many('rent.cash', 'sale_id')
    cash_outstanding = fields.Float(string=_('Balance'), compute='total_balance_amount')

    @api.depends('end_date')
    def calculate_days(self):
        for r in self:
            r.date_rent = 1
            if r.end_date:
                r.date_rent = (self.end_date - self.date_order.date()).days + 1

    @api.depends('cash_detail', 'amount_total')
    def total_balance_amount(self):
        for r in self:
            r.cash_outstanding = r.amount_total
            payment = sum(r.cash_detail.mapped('cash') or [0])
            r.cash_outstanding = r.amount_total - payment

    def open_payment(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'rent.cash',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_sale_id': self.id,
                        'from_sale': True},
            'nodestroy': True,
        }