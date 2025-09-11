# lww_custom_view/models/account_move.py
from odoo import api, fields, models

class AccountMove(models.Model):
    _inherit = "account.move"

    # Internal manual storage to allow override from wizards or manual edits
    project_id_manual = fields.Many2one(
        "project.project",
        string="Project (Manual)",
        help="Internal field to store manually overridden Project.",
        copy=False,
    )

    # Project on invoice/journal entry
    # - If manual override exists -> use it
    # - Else, for customer invoices/credit notes derive from originating SO
    project_id = fields.Many2one(
        "project.project",
        string="Project",
        compute="_compute_project_id",
        inverse="_inverse_project_id",
        store=True,
        readonly=False,
        index=True,
        help=(
            "Project linked to this entry. If set manually, it overrides the value\n"
            "derived from the originating Sales Order for customer invoices."
        ),
    )

    @api.depends("project_id_manual", "invoice_line_ids.sale_line_ids.order_id.project_id", "move_type")
    def _compute_project_id(self):
        for move in self:
            # Respect manual override when present
            if move.project_id_manual:
                move.project_id = move.project_id_manual
                continue

            proj = False
            if move.move_type in ("out_invoice", "out_refund"):
                orders = move.invoice_line_ids.mapped("sale_line_ids").mapped("order_id")
                if orders:
                    projs = orders.mapped("project_id")
                    proj = projs[0] if projs else False
            move.project_id = proj

    def _inverse_project_id(self):
        for move in self:
            move.project_id_manual = move.project_id
