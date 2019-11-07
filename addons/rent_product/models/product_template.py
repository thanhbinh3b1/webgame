# __author__ = 'BinhTT'
from odoo import fields, api, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    rent_type = fields.Selection([('1', '1'), ('2', '2'), ('3', '3')], string='Loai')

    @api.model
    def create(self, vals):
        cate_obj = self.env['product.category'].browse(vals.get('categ_id'))
        vals.update(default_code=cate_obj.code or '' + str(cate_obj.sequence))
        cate_obj.sequence += 1
        res = super(ProductTemplate, self).create(vals)

        return res