from odoo import models, api


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _get_sale_order_line_multiline_description_sale(self):
        self.ensure_one()
        description = (
            ""
            + self._get_sale_order_line_multiline_description_variants()
        )
        if self.linked_line_id and not self.combo_item_id:
            description += "\n" + _("Option for: %s", self.linked_line_id.product_id.display_name)
        if self.linked_line_ids and self.product_type != 'combo':
            description += "\n" + "\n".join([
                _("Option: %s", linked_line.product_id.display_name)
                for linked_line in self.linked_line_ids
            ])
        return description