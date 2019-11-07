# __author__ = 'BinhTT'
from odoo import models, fields, api


class RentPriceList(models.Model):
    _name = 'rent.pricelist'

    name = fields.Char('Name')
    rent_type = fields.Selection([('1', '1'), ('2', '2'), ('3', '3')], string='Loai')
    rent_detail = fields.One2many('rent.pricelist.detail', 'rent_price_id')


class RentPriceDetail(models.Model):
    _name = 'rent.pricelist.detail'
    rent_price_id = fields.Many2one('rent.pricelist')
    from_day = fields.Integer('From (Day)')
    to_day = fields.Integer('To (Day)')
    price = fields.Float('Price')