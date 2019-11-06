# __author__ = 'BinhTT'

from openerp import models, fields, api
import openerp.addons.decimal_precision as dp
from openerp.tools import float_compare


class NpStockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.model
    def _get_invoice_vals(self, key, inv_type, journal_id, move,):
        res = super(NpStockPicking, self)._get_invoice_vals(key, inv_type, journal_id, move)
        if inv_type == 'out_invoice':
            sale = move.picking_id.sale_id
            res.update({
                'ws_discount_type': sale.ws_discount_type,
                'ws_discount_percent': sale.ws_discount_percent
            })
        if inv_type == 'in_invoice':
            purchase = move.picking_id.purchase_id
            res.update({
                'ws_discount_type': purchase.ws_discount_type,
                'ws_discount_percent': purchase.ws_discount_percent
            })

        return res


class NPStockMove(models.Model):
    _inherit = 'stock.move'

    @api.model
    def _get_invoice_line_vals(self, move, partner, inv_type):
        """ Gets price unit for invoice
        @param move_line: Stock move lines
        @param type: Type of invoice
        @return: The price unit for the move line
       """
        res = super(NPStockMove, self)._get_invoice_line_vals(move, partner, inv_type)
        # res['discount_amount'] = 0
        if (inv_type == 'in_invoice' and move.purchase_line_id) or\
                (inv_type == 'in_refund' and move.origin_returned_move_id):
            purchase_line = move.purchase_line_id or move.origin_returned_move_id.purchase_line_id
            # res['invoice_line_tax_id'] = [(6, 0, [x.id for x in purchase_line.taxes_id])]
            # res['price_unit'] = purchase_line.price_unit * (1 - ( or 1) / 100)
            res.update(purchase_line_id=purchase_line.id,
                       discount=purchase_line.discount,
                       ws_discount=purchase_line.ws_discount * (res['quantity'] / purchase_line.product_qty),
                       price_unit = purchase_line.price_unit * (move.product_uom.factor_inv / purchase_line.product_uom.factor_inv))
            # res['discount_amount'] = purchase_line.discount
        if inv_type in ('out_invoice', 'out_refund') and move.sale_line_id:
            res.update(sale_line_id=move.sale_line_id.id,
                       ws_discount=move.sale_line_id.ws_discount * (res['quantity'] / move.sale_line_id.product_uom_qty)
                       )
        return res
