from odoo import api, models


class AccountTax(models.Model):
    _inherit = "account.tax"

    def _convert_to_tax_base_line_dict(self, base_line, **kwargs):
        res = super()._convert_to_tax_base_line_dict(base_line, **kwargs)
        if (base_line and 
            hasattr(base_line, 'discount_fixed') and 
            base_line.discount_fixed and 
            base_line._name in ["sale.order.line", "account.move.line"]):
            res["discount"] = base_line._get_discount_from_fixed_discount()
        return res
