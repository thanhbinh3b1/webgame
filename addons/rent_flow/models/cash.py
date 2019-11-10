# __author__ = 'BinhTT'
from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp


class RentCash(models.Model):
    _name = 'rent.cash'

    cash_type = fields.Selection([('in', _('Cash In')), ('out', _('Cash Out'))])
    cash = fields.Float('$', digits=dp.get_precision('Account'),)
    sale_id = fields.Many2one('sale.order')
    reason = fields.Char('Reason')

    def save_payment(self):
        return {'type': 'ir.actions.act_window_close'}

    @api.model
    def create(self, vals):
        if vals.get('cash_type') == 'out':
            vals.update({'cash': vals.get('cash', 0) * -1})
        if self._context.get('from_sale', False):
            reason = 'Receive of '
            if vals.get('cash_type') == 'out':
                reason = 'Pay of '
            vals.update({'reason': reason + self._context.get('from_name', '')})

        res = super(RentCash, self).create(vals)
        if self._context.get('from_sale', False):
            {'type': 'ir.actions.act_window_close'}
        return res