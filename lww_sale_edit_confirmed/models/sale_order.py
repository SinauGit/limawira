from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    edit_confirmed_allowed = fields.Boolean(
        compute='_compute_edit_confirmed_allowed',
        help="Technical field: True if current user is allowed to edit "
             "Customer/UoM on a confirmed Sales Order.",
    )

    def _compute_edit_confirmed_allowed(self):
        allowed = self.env.user.has_group(
            'lww_sale_edit_confirmed.group_sale_edit_confirmed'
        )
        for order in self:
            order.edit_confirmed_allowed = allowed

    @api.onchange('partner_id')
    def _onchange_partner_id_edit_confirmed_warning(self):
        if self.state == 'sale' and any(
            line.qty_invoiced > 0 for line in self.order_line
        ):
            return {
                'warning': {
                    'title': "SO Sudah Diinvoice",
                    'message': (
                        "SO ini sudah memiliki invoice terkait. Perubahan "
                        "Customer TIDAK akan otomatis mengubah invoice yang "
                        "sudah dibuat sebelumnya."
                    ),
                }
            }
