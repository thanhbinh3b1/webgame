# __author__ = 'BinhTT'
from odoo import models, fields, api, _


class RentCash(models.Model):
    _name = 'rent.cash'

    cash_type = fields.Selection([('in', _('Cash In')), ('out', _('Cash Out'))])
    cash = fields.Float('$')
    sale_id = fields.Many2one('sale.order')

    def save_payment(self):
        return {'type': 'ir.actions.act_window_close'}
