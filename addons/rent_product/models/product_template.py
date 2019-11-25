# __author__ = 'BinhTT'
from odoo import fields, api, models


class ProductTemplate(models.Model):
    _inherit = "product.template"
    _order = "default_code, name"


    rent_type = fields.Many2one('rent.product.type', string='Loai')

    @api.model
    def create(self, vals):
        cate_obj = self.env['product.category'].browse(vals.get('categ_id'))
        vals.update(default_code=(cate_obj.code or '') + str(cate_obj.sequence))
        cate_obj.sequence += 1
        res = super(ProductTemplate, self).create(vals)

        return res