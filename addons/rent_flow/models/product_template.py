# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging

from odoo import api, fields, models, _
from odoo.addons.base.models.res_partner import WARNING_MESSAGE, WARNING_HELP
from odoo.tools.float_utils import float_round

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    sales_count = fields.Float(compute='_compute_sales_count', string='Sold')

    @api.depends('product_variant_ids.sales_count')
    def _compute_sales_count(self):
        for product in self:
            product.sales_count = float_round(sum([p.sales_count for p in product.with_context(active_test=False).product_variant_ids]), precision_rounding=product.uom_id.rounding)

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
