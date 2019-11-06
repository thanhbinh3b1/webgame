# __author__ 'trananhdung'

from openerp import models, fields, api


class AccountingConfig(models.TransientModel):
    _inherit = 'account.config.settings'

    @api.model
    def get_default_discount_account_config(self, fields):
        return {'discount_account_config': self.get_discount_account_config()}

    @api.model
    def get_discount_account_config(self):
        return eval(self.env['ir.config_parameter'].get_param('np_discount.discount_account_id_value') or 'False')

    @api.multi
    def set_default_discount_account_id(self):
        self.ensure_one()
        self.env['ir.config_parameter'].set_param('np_discount.discount_account_id_value',
                                                  self.discount_account_config.id)

    discount_account_config = fields.Many2one(comodel_name='account.account', string='Discount Account')
