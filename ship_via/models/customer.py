from odoo import models, fields, api

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    
    is_po_service = fields.Boolean(
        string='PO Service',
        default=False,
        help="Indicates if this purchase order is for services"
    )
    
    customer_id = fields.Many2one(
        comodel_name='res.partner',
        string='Customer',
        domain="[('customer_rank', '>', 0)]",  # opsional: hanya tampilkan partner bertipe customer
        help="Customer terkait dengan purchase order ini (tidak sama dengan supplier/vendor).",
    )