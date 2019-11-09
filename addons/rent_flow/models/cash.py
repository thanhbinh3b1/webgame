# __author__ = 'BinhTT'
from odoo import models, fields, api, _


class RentCash(models.Model):
    _name = 'rent.cash'

    cash_type = fields.Selection([('in', _('Cash In')), ('out', _('Cash Out'))])
    cash = fields.Float('$')
    sale_id = fields.Many2one('sale.order')

    def save_payment(self):
        return {'type': 'ir.actions.act_window_close'}

    @api.model
    def create(self, vals):
        if vals.get('cash_type') == 'out':
            vals.update({'cash': vals.get('cash', 0) * -1})
        res = super(RentCash, self).create(vals)
        return res