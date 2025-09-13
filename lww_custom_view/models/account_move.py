# lww_custom_view/models/account_move.py
from odoo import api, fields, models

class AccountMove(models.Model):
    _inherit = "account.move"

    # Project on invoice, computed from originating Sales Order(s)
    project_id = fields.Many2one(
        "project.project",
        string="Project",
        compute="_compute_project_id",
        store=True,
        readonly=True,
        index=True,
        help="Automatically set from the originating Sales Order's Project."
    )

    @api.depends("invoice_line_ids.sale_line_ids.order_id.project_id", "move_type")
    def _compute_project_id(self):
        """
        Rule:
        - Only for customer invoices/credit notes.
        - Collect SOs from invoice lines -> take their project(s).
        - If multiple projects, pick the first non-empty (can be adjusted).
        """
        for move in self:
            proj = False
            if move.move_type in ("out_invoice", "out_refund"):
                orders = move.invoice_line_ids.mapped("sale_line_ids").mapped("order_id")
                if orders:
                    projs = orders.mapped("project_id")
                    proj = projs[0] if projs else False
            move.project_id = proj
