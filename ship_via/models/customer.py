from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

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
    
    @api.constrains('is_po_service', 'customer_id')
    def _check_customer_required(self):
        for record in self:
            if record.is_po_service and not record.customer_id:
                raise ValidationError(_("Customer harus diisi ketika PO Service diaktifkan."))
                
    @api.onchange('is_po_service') 
    def _onchange_is_po_service(self):
        """Reset customer_id when is_po_service is turned off"""
        if not self.is_po_service:
            self.customer_id = False