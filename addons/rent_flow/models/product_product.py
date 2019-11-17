# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import timedelta, time
from odoo import api, fields, models
from odoo.tools.float_utils import float_round


class ProductProduct(models.Model):
    _inherit = 'product.product'

    sales_count = fields.Float(compute='_compute_sales_count', string='Sold')

    def _compute_sales_count(self):
        r = {}
        self.sales_count = 0
        if not self.user_has_groups('sales_team.group_sale_salesman'):
            return r
        domain = [
            ('state', '=', 'sale'),
            ('product_id', 'in', self.ids),
        ]
        for product in self:
            if not product.id:
                product.sales_count = 0.0
                continue
            product.sales_count = self.env['sale.order.line'].search_count(domain)
        return r

    def action_view_sales(self):
        view_id = self.env.ref('rent_flow.rent_view_order_line_tree').id
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order.line',
            'view_mode': 'tree',
            'view_id': view_id,
            'views': [(view_id, 'tree')],

            'target': 'current',
            'domain': [('product_id', 'in', self.ids)],
            'context': {'search_default_sale_state': 1},
        }

