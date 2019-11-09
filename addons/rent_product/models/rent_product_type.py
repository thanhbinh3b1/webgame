# __author__ = 'BinhTT'
from odoo import fields, api, models


class RentType(models.Model):
    _name = 'rent.product.type'

    name = fields.Char('Name')