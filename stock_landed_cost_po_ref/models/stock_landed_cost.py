from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class StockLandedCost(models.Model):
    _inherit = "stock.landed.cost"

    vendor_bill_amount_total = fields.Monetary(
        string='Total Vendor Bill',
        related='vendor_bill_id.amount_total',
        # currency_field='vendor_bill_currency_id',
        store=True,
        readonly=True,
    )

    purchase_order_id = fields.Many2one(
        "purchase.order",
        string="Purchase Order",
        compute="_compute_purchase_order_id",
        readonly=True,
        store=False,
    )

    @api.depends(
        "picking_ids",
        "picking_ids.move_ids_without_package.purchase_line_id.order_id",
        "picking_ids.origin",
    )
    def _compute_purchase_order_id(self):
        for lc in self:
            order = lc._get_single_po_from_pickings(lc.picking_ids)
            lc.purchase_order_id = order or False

    def _get_single_po_from_pickings(self, pickings):

        PO = self.env["purchase.order"]

        orders = pickings.mapped("move_ids_without_package.purchase_line_id.order_id")
        orders = orders.exists()
        if not orders:

            names = list({o for o in pickings.mapped("origin") if o})
            if names:
                orders = PO.search([("name", "in", names)])
        if len(orders) == 1:
            return orders[0]
        return None

    @api.constrains("picking_ids")
    def _check_pickings_same_po(self):
        for lc in self:
            if not lc.picking_ids:
                continue
            order = lc._get_single_po_from_pickings(lc.picking_ids)
            if not order:

                raise ValidationError(_("Transfer or No Receipt is not the same, it should be the same"))

    @api.onchange("picking_ids")
    def _onchange_pickings_warn(self):

        if self.picking_ids:
            order = self._get_single_po_from_pickings(self.picking_ids)
            if not order:
                return {
                    "warning": {
                        "title": _("Peringatan"),
                        "message": _("Transfer or No Receipt is not the same, it should be the same"),
                    }
                }
