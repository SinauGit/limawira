from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class StockLandedCost(models.Model):
    _inherit = "stock.landed.cost"

    # 1 PO saja, readonly, ditentukan dari Transfers (receipt)
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
        """Kembalikan 1 PO jika semua receipt berasal dari PO yang sama,
        kalau tidak cocok atau kosong -> None.
        """
        PO = self.env["purchase.order"]
        # Sumber utama: relasi purchase_line_id pada stock.move
        orders = pickings.mapped("move_ids_without_package.purchase_line_id.order_id")
        orders = orders.exists()
        if not orders:
            # Fallback: cocokkan 'origin' dengan nama PO
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
                # Block agar user tidak bisa simpan konfigurasi yang salah
                raise ValidationError(_("Transfer or No Receipt is not the same, it should be the same"))

    @api.onchange("picking_ids")
    def _onchange_pickings_warn(self):
        """Kasih warning dini saat user memilih receipt yang tidak seragam PO-nya."""
        if self.picking_ids:
            order = self._get_single_po_from_pickings(self.picking_ids)
            if not order:
                return {
                    "warning": {
                        "title": _("Peringatan"),
                        "message": _("Transfer or No Receipt is not the same, it should be the same"),
                    }
                }
