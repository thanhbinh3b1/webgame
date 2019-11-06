# __author__ = 'BinhTT'

from odoo import models, fields, api
import odoo.addons.decimal_precision as dp
from odoo.tools import float_is_zero
import logging
import datetime as dt
import multiprocessing

CPU_CORES = min(multiprocessing.cpu_count(), 20)
_logger = logging.getLogger(__name__)


class NpAccountInvoice(models.Model):
    _inherit = 'account.invoice'

    # def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False, lazy=True):
    #     res = super(NpAccountInvoice, self).read_group(cr, uid, domain, fields, groupby, offset, limit=limit, context=context,
    #                                                    orderby=orderby, lazy=lazy)
    #
    #     if 'ws_discount_amount_display' or 'total_before_discount_display' or 'amount_total_display' or\
    #             'residual_display' or 'base_residual_display' in fields:
    #         for line in res:
    #             if '__domain' in line:
    #                 lines = self.search(cr, uid, line['__domain'], context=context)
    #                 discount_sum = 0.0
    #                 total_before_discount_sum = 0.0
    #                 total_sum = 0.0
    #                 bal_sum = 0.0
    #                 base_bal_sum = 0.0
    #                 for current_account in self.browse(cr, uid, lines, context=context):
    #                     discount_sum += current_account.ws_discount_amount_display
    #                     total_before_discount_sum += current_account.total_before_discount
    #                     total_sum += current_account.amount_total_display
    #                     bal_sum += current_account.residual_display
    #                     base_bal_sum += current_account.base_residual_display
    #
    #                 line['total_before_discount_display'] = total_before_discount_sum
    #                 line['ws_discount_amount_display'] = discount_sum
    #                 line['amount_total_display'] = total_sum
    #                 line['residual_display'] = bal_sum
    #                 line['base_residual_display'] = base_bal_sum
    #
    #     return res
    @api.multi
    @api.depends('type')
    def _display_amount(self):
        res = {'value': {}}
        for line in self:
            # if line.type == 'out_refund' and line.amount_total > 0:
            #     line.amount_untaxed = - line.amount_untaxed
            #     line.total_before_discount = - line.total_before_discount
            #     line.amount_total = - line.amount_total
            #     line.residual = - line.residual
            #     line.base_residual = - line.base_residual
            # else:
            #     line.amount_untaxed = line.amount_untaxed
            #     line.total_before_discount = line.total_before_discount
            #     line.amount_total = line.amount_total
            #     line.residual = line.residual
            #     line.base_residual = line.base_residual

            if line.ws_discount_amount:
                line.ws_discount_amount_display = line.ws_discount_amount
            else:
                line.ws_discount_amount_display = 0.00

    # amount_untaxed = fields.Float(default='_display_amount')
    base_residual = fields.Float()
    # ws_discount_amount_display = fields.Float(digits=(16, 2), compute='_display_amount')

    @api.multi
    @api.depends(
        'state', 'currency_id', 'invoice_line.price_subtotal',
        'move_id.line_id.account_id.type',
        'move_id.line_id.amount_residual',
        'move_id.line_id.reconcile_id',
        'move_id.line_id.amount_residual_currency',
        'move_id.line_id.currency_id',
        'move_id.line_id.reconcile_partial_id.line_partial_ids.invoice.type',
    )
    def _compute_test_residual_amount(self):
        for r in self:
            if r.type in ['out_refund', 'in_refund', 'np_in_refund']:
                # r.get_value_test_residual()
                r.test_residual = -r.residual
                r.test_base_residual = -r.base_residual
                r.test_total_amt = -r.amount_total
                r.test_amount_untaxed = -r.amount_untaxed
                r.test_amount_tax = -r.amount_tax
            else:
                r.test_residual = r.residual
                r.test_base_residual = r.base_residual
                r.test_total_amt = r.amount_total
                r.test_amount_untaxed = r.amount_untaxed
                r.test_amount_tax = r.amount_tax

    # test_residual and test_base_residual show value of residual and base_residual when type = out_refund
    test_residual = fields.Float(compute='_compute_test_residual_amount', store=True)
    test_base_residual = fields.Float(compute='_compute_test_residual_amount', store=True)
    test_total_amt = fields.Float(compute='_compute_test_residual_amount', store=True)
    test_amount_untaxed = fields.Float(compute='_compute_test_residual_amount', store=True)
    test_amount_tax = fields.Float(compute='_compute_test_residual_amount', store=True)

    @api.multi
    def write(self, vals):
        res = super(NpAccountInvoice, self).write(vals)
        for r in self:
            if self.env.context.get('need_recompute_discount') and not vals.get('ws_discount_type', False):
                if r.ws_discount_type:
                    self.env['global_discount.wizard'].with_context(
                        active_ids=r.ids,
                        active_id=r.ids[0],
                        active_model=self._name,
                        need_recompute_discount=False
                    ).recompute_discount()
                    r.with_context(need_recompute_discount=False).button_compute()
        return res

    # @api.one
    # @api.depends('invoice_line')
    # def _compute_discount(self):
    #     discount_total = 0.0
    #     untax_discount_total = 0.0
    #     for line in self.invoice_line:
    #         if line.product_id and line.product_id.name == 'Discount':
    #             discount_total += line.price_unit
    #         else:
    #             untax_discount_total += line.price_subtotal
    #     if discount_total == 0.0:
    #         self.flag_discount=False
    #     else:
    #         self.flag_discount=True
    #     self.discount_rate = abs(discount_total)
    #     self.untax_discount = untax_discount_total

    # @api.multi
    # @api.depends('invoice_line', 'tax_line.amount')
    def _compute_amount_thread(self, result=None):
        if result is None:
            result = {}
        # with api.Environment.manage():
        env = api.Environment(self.pool.cursor(), self._uid, self.env.context.copy())

        # for invoice in self.with_env(env).browse(self.ids):
        for invoice in self:
            # try:
            total_before_discount = sum([line.quantity * line.price_unit for line in invoice.invoice_line])
            discount_amount = sum([line.ws_discount + line.quantity * line.price_unit * line.discount / 100 for line in
                                   invoice.invoice_line])
            ws_discount_amount = sum([line.ws_discount for line in invoice.invoice_line])
            total_before_ws_discount = sum([line.price_subtotal for line in invoice.invoice_line])
            amount_tax = sum(line.amount for line in invoice.tax_line)
            amount_untaxed = total_before_ws_discount - ws_discount_amount
            amount_total = amount_untaxed + amount_tax
            ws_discount_amount = ws_discount_amount
            total_before_ws_discount = total_before_ws_discount
            amount_untaxed = amount_untaxed
            amount_tax = amount_tax
            result[invoice.id] = {
                'total_before_discount': total_before_discount,
                'discount_amount': discount_amount,
                'ws_discount_amount': ws_discount_amount,
                'total_before_ws_discount': total_before_ws_discount,
                'amount_total': amount_total,
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax
            }
            # except Exception as e:
            #     _logger.error(e.__repr__())
            # finally:
            #     print result

            # env.cr.close()

    @api.multi
    @api.depends('invoice_line', 'tax_line', 'invoice_line.price_subtotal',
                 'invoice_line.ws_discount', 'invoice_line.quantity',
                 'invoice_line.discount', 'invoice_line.ws_discount', 'invoice_line.price_unit')
    def _compute_amount(self):
        _logger.info("ACCOUNT INVOICE: Start compute discount field on %s records!" % len(self.ids))
        t1 = dt.datetime.now()

        for invoice in self:
            total_before_discount = sum([line.quantity * line.price_unit for line in invoice.invoice_line])
            discount_amount = sum([line.ws_discount + line.quantity * line.price_unit * line.discount / 100 for line in
                                   invoice.invoice_line])
            ws_discount_amount = sum([line.ws_discount for line in invoice.invoice_line])
            total_before_ws_discount = sum([line.price_subtotal for line in invoice.invoice_line])
            amount_untaxed = total_before_ws_discount - ws_discount_amount
            amount_tax = sum(line.amount for line in invoice.tax_line)

            invoice.amount_total = amount_untaxed + amount_tax
            invoice.amount_tax = amount_tax
            invoice.amount_untaxed = amount_untaxed
            invoice.total_before_discount = total_before_discount
            invoice.discount_amount = discount_amount
            invoice.ws_discount_amount = ws_discount_amount
            invoice.total_before_ws_discount = total_before_ws_discount

        time_delta = dt.datetime.now() - t1
        _logger.info("ACCOUNT INVOICE: Running Time for %s records: %s" % (len(self.ids), time_delta.total_seconds()))

    # flag_discount = fields.Boolean(string='Discount Flag', default=False)
    # discount_rate = fields.Float(string='Discount Total', digits_compute=dp.get_precision('Account'),
    #                              readonly=True)

    ws_discount_amount = fields.Float(string='Whole Bill Discount Amount', digits=(16, 8),
                                      compute='_compute_amount', store=True, help='Discount Amount on whole bill')
    ws_discount_type = fields.Selection(selection=[('amount', 'Fixed Amount'), ('percent', 'Percentage')],
                                        string='Whole Bill Discount Type', readonly=True)
    # ws_discount_amount = fields.Float(string='Whole Bill Discount', digits=dp.get_precision('Account'),
    #                                   readonly=True)
    ws_discount_percent = fields.Float(string='Whole Bill Discount (%)', digits=dp.get_precision('Discount'),
                                       readonly=True)

    # discount_amount = fields.Float(string='Discount Amount', digits_compute=dp.get_precision('Account'),
    discount_amount = fields.Float(string='Discount Amount', digits=(16, 8),
                                   compute='_compute_amount', store=True, help='Total discount amount\n'
                                                                               'This value equal discount whole bill'
                                                                               ' and total discount on line')
    total_before_ws_discount = fields.Float(string='Total Amount Before Discount Whole Bill', compute='_compute_amount',
                                            help='The total Amount after discount on line'
                                                 ' before discount whole bill and without tax', store=True)

    total_before_discount = fields.Float(string='Total Amount Before Discount', compute='_compute_amount',
                                         help='Total Amount without any discount and tax', store=True)
    amount_untaxed = fields.Float(
        string='Untaxed Amount', digits=dp.get_precision('Account'),
        store=True, readonly=True, compute='_compute_amount', track_visibility='always',
        help='Amount after Discount and without tax'
    )
    amount_tax = fields.Float(
        string='Tax', digits=dp.get_precision('Account'),
        store=True, readonly=True, compute='_compute_amount', help='Tax Amount base on amount_untaxed')
    amount_total = fields.Float(
        string='Total', digits=dp.get_precision('Account'),
        store=True, readonly=True, compute='_compute_amount', help='Net Total Amount')

    # @Debugging
    @api.model
    def create(self, vals):
        invoice = super(NpAccountInvoice, self).create(vals)
        return invoice


class NpAccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    @api.multi
    @api.depends('sale_line_id')
    def _compute_ws_discount(self):
        for line in self:
            if line.sale_line_id.id:
                line.ws_discount = line.sale_line_id.ws_discount * (line.quantity / line.sale_line_id.product_uom_qty)
            elif line.purchase_line_id.id:
                # TODO: compute whole bill discount on purchase order
                pass

    ws_discount = fields.Float(string='Discount Amount',
                               # compute='_compute_ws_discount',
                               digits=(16, 8),
                               help='This value equal (Whole Bill Discount)*(Line Quantity)/(Total Quantity on Bill) '
                                    'and should be invisible')

    # total_bf_discount = fields.Float(compute="_amount_line_discount", string='Amount', digits=dp.get_precision('Account'))

    # @api.one
    # @api.depends('price_unit', 'discount', 'invoice_line_tax_id', 'quantity',
    #              'product_id', 'invoice_id.partner_id', 'invoice_id.currency_id')
    # def _amount_line_discount(self):
    #     price = self.price_unit
    #     taxes = self.invoice_line_tax_id.compute_all(price, self.quantity, product=self.product_id,
    #                                                  partner=self.invoice_id.partner_id)
    #     self.price_subtotal = taxes['total']
    #     if self.invoice_id:
    #         self.total_bf_discount = self.invoice_id.currency_id.round(self.price_subtotal)

    @api.model
    def move_line_get_item(self, line):
        result = super(NpAccountInvoiceLine, self).move_line_get_item(line)
        if line.invoice_id.type in ('out_invoice', 'out_refund', 'out_invoice_dn'):
            result.update(price=(line.quantity * line.price_unit))
        if line.invoice_id.type in ('in_invoice', 'in_refund'):
            result.update(price=(line.price_subtotal - line.ws_discount),
                          final_price_unit=line.purchase_line_id.final_price_unit)
        return result

    @api.model
    def invoice_line_move_line_get(self, invoice_id):
        res = super(NpAccountInvoiceLine, self).invoice_line_move_line_get(invoice_id)
        invoice = self.env['account.invoice'].browse(invoice_id)
        discount_account_id = self.env['account.config.settings'].get_discount_account_config()
        tax_sign = -1
        if res[0].get('taxes', False) and invoice.type not in ('out_invoice', 'out_invoice_dn', 'in_invoice'):
            tax = res[0].get('taxes', False)
            tax_sign = tax['base_sign']
        if not float_is_zero(value=invoice.discount_amount,
                             precision_digits=self.env['decimal.precision'].precision_get('Account')) \
                and invoice.type in ('out_invoice', 'out_refund', 'out_invoice_dn'):
            res.append({
                'account_id': discount_account_id,
                'name': 'Discount',
                'price': -invoice.discount_amount,
                'quantity': 1,
                'price_unit': invoice.discount_amount,
                'account_analytic_id': False,
                'tax_code_id': res[0].get('tax_code_id', False),
                'tax_amount': invoice.discount_amount * tax_sign
            })

        # if not float_is_zero(value=invoice.discount_amount,
        #                      precision_digits=self.env['decimal.precision'].precision_get('Account')) \
        #         and invoice.type in ('in_invoice', 'in_refund'):
        #     print res
        return res

    @api.model
    def create(self, vals):
        r = super(NpAccountInvoiceLine, self).create(vals)
        return r


class AccountInvoiceTax(models.Model):
    _inherit = 'account.invoice.tax'

    @api.v8
    def compute(self, invoice):
        tax_grouped = {}
        currency = invoice.currency_id.with_context(date=invoice.date_invoice or fields.Date.context_today(invoice))
        company_currency = invoice.company_id.currency_id
        for line in invoice.invoice_line:
            taxes = line.invoice_line_tax_id.compute_all(
                ((line.price_unit * (
                        1 - (line.discount or 0.0) / 100.0)) * line.quantity - line.ws_discount) / line.quantity,
                line.quantity, line.product_id, invoice.partner_id)['taxes']
            for tax in taxes:
                val = {
                    'invoice_id': invoice.id,
                    'name': tax['name'],
                    'amount': tax['amount'],
                    'manual': False,
                    'sequence': tax['sequence'],
                    'base': currency.round(tax['price_unit'] * line['quantity']),
                    # 'account_tax_id': tax['account_tax_id']
                }
                if invoice.type in ('out_invoice', 'in_invoice', 'out_invoice_dn', 'np_in_invoice'):
                    val['base_code_id'] = tax['base_code_id']
                    val['tax_code_id'] = tax['tax_code_id']
                    val['base_amount'] = currency.compute(val['base'] * tax['base_sign'], company_currency, round=False)
                    val['tax_amount'] = currency.compute(val['amount'] * tax['tax_sign'], company_currency, round=False)
                    val['account_id'] = tax['account_collected_id'] or line.account_id.id
                    val['account_analytic_id'] = tax['account_analytic_collected_id']
                else:
                    val['base_code_id'] = tax['ref_base_code_id']
                    val['tax_code_id'] = tax['ref_tax_code_id']
                    val['base_amount'] = currency.compute(val['base'] * tax['ref_base_sign'], company_currency,
                                                          round=False)
                    val['tax_amount'] = currency.compute(val['amount'] * tax['ref_tax_sign'], company_currency,
                                                         round=False)
                    val['account_id'] = tax['account_paid_id'] or line.account_id.id
                    val['account_analytic_id'] = tax['account_analytic_paid_id']

                # If the taxes generate moves on the same financial account as the invoice line
                # and no default analytic account is defined at the tax level, propagate the
                # analytic account from the invoice line to the tax line. This is necessary
                # in situations were (part of) the taxes cannot be reclaimed,
                # to ensure the tax move is allocated to the proper analytic account.
                if not val.get('account_analytic_id') and line.account_analytic_id \
                        and val['account_id'] == line.account_id.id:
                    val['account_analytic_id'] = line.account_analytic_id.id

                key = (val['tax_code_id'], val['base_code_id'], val['account_id'])
                if key not in tax_grouped:
                    tax_grouped[key] = val
                else:
                    tax_grouped[key]['base'] += val['base']
                    tax_grouped[key]['amount'] += val['amount']
                    tax_grouped[key]['base_amount'] += val['base_amount']
                    tax_grouped[key]['tax_amount'] += val['tax_amount']

        for t in tax_grouped.values():
            t['base'] = currency.round(t['base'])
            t['amount'] = currency.round(t['amount'])
            t['base_amount'] = currency.round(t['base_amount'])
            t['tax_amount'] = currency.round(t['tax_amount'])

        return tax_grouped


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.model
    def create(self, vals):
        obj = super(AccountMoveLine, self).create(vals)
        return obj
