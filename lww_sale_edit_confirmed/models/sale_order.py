from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    can_lock_unlock = fields.Boolean(
        compute='_compute_can_lock_unlock',
        help="Technical field: True if the current user may Lock/Unlock "
             "this order. Matches Sales access rights: 'Administrator' can "
             "Lock/Unlock any order; 'User: Own Documents Only' can "
             "Lock/Unlock only orders where they are the Salesperson.",
    )

    @api.depends('user_id')
    def _compute_can_lock_unlock(self):
        user = self.env.user
        # Sales > Access Rights: Administrator
        is_admin = user.has_group('sales_team.group_sale_manager')
        # Sales > Access Rights: User: Own Documents Only
        # (group_sale_salesman without the "All Documents" upgrade)
        is_own_docs_only = (
            user.has_group('sales_team.group_sale_salesman')
            and not user.has_group('sales_team.group_sale_salesman_all_leads')
        )
        for order in self:
            order.can_lock_unlock = is_admin or (
                is_own_docs_only and order.user_id == user
            )

    @api.onchange('partner_id')
    def _onchange_partner_id_edit_confirmed_warning(self):
        if (
            self.state == 'sale'
            and not self.locked
            and any(line.qty_invoiced > 0 for line in self.order_line)
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
