# __author__ = 'BinhTT'
from odoo import fields, api, models


class productCate(models.Model):
    _inherit = 'product.category'

    code = fields.Char(string='Code')
    sequence = fields.Integer('Sequence')