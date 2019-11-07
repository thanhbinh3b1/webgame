# __author__ = 'BinhTT'
from odoo import fields, api, models


class saleOrder(models.Model):
    _inherit = 'sale.order'

    end_date = fields.Date(string='End Date')
    date_rent = fields.Integer('Days', compute='calculate_days')

    @api.depends('end_date')
    def calculate_days(self):
        for r in self:
            r.date_rent = 1
            if r.end_date:
                r.date_rent = (self.end_date - self.date_order.date()).days