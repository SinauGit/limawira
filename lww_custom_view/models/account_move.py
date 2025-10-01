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



    move_type = fields.Selection(
        selection_add=[
            ('expense', 'Expense'),
        ],
        ondelete={'expense': 'cascade'}
    )

    @api.depends('move_type')
    def _compute_move_type_display(self):
        """Override untuk menambahkan display name untuk expense"""
        super()._compute_move_type_display()
        for move in self:
            if move.move_type == 'expense':
                move.move_type_display = 'Expense'

    def _get_default_journal(self):
        """Override untuk menentukan journal default untuk expense"""
        if self.move_type == 'expense':
            return self.env['account.journal'].search([
                ('type', '=', 'purchase'),
                ('company_id', '=', self.company_id.id)
            ], limit=1)
        return super()._get_default_journal()
