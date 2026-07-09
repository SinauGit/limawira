from odoo import fields, models


class ResConfigSettings(models.TransientModel):
                                                                             
    _inherit = 'res.config.settings'

    po_deposit_default_product_id = fields.Many2one(
        'product.product',
        'PO Deposit Product',
        domain="[('type', '=', 'service')]",
        config_parameter='purchase_down_payment.po_deposit_default_product_id',
        help='Default product used for payment advances in purchase order')
