from odoo import api, fields, models, _
from odoo.exceptions import UserError

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    is_downpayment = fields.Boolean(
        string="Is a down payment", help="Down payments are made when "
                                         "creating Bills from a purchase order."
                                         "They are not copied when "
                                         "duplicating a purchase order.")

    @api.ondelete(at_uninstall=False)
    def _unlink_except_purchase_or_done(self):
        for line in self:
            if line.is_downpayment and not line.invoice_lines:
                continue
            if line.order_id.state in ['purchase', 'done']:
                state_description = {state_desc[0]: state_desc[1] for state_desc in self._fields['state']._description_selection(self.env)}
                raise UserError(_('Cannot delete a purchase order line which is in state “%s”.', state_description.get(line.state)))

    def _prepare_invoice_line(self, **optional_values):           
        self.ensure_one()
        res = {
            'display_type': 'product',
            'sequence': self.sequence,
            'name': self.name,
            'product_id': self.product_id.id,
            'product_uom_id': self.product_uom.id,
            'quantity': self.qty_to_invoice,
            'price_unit': self.price_unit,
            'purchase_line_id': self.id,
        }
        if optional_values:
            res.update(optional_values)
        if self.display_type:
            res['account_id'] = False
        return res
