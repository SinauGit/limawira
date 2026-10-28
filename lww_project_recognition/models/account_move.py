from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    lww_project_id = fields.Many2one('project.project', string='Recognition Project', index='btree_not_null', copy=False)
    lww_picking_id = fields.Many2one('stock.picking', string='Recognition DO', index='btree_not_null', copy=False)
    lww_entry_type = fields.Selection([
        ('reclass', 'Reclass'),
        ('backdated', 'Backdated'),
        ('reversal_reclass', 'Reclass Reversal'),
        ('reversal_backdated', 'Backdated Reversal'),
    ], string='Recognition Entry', copy=False, index='btree_not_null')
    lww_product_id = fields.Many2one('product.product', string='Recognition Product', index='btree_not_null', copy=False)
    lww_recognition_year = fields.Integer(string='Recognition Year', copy=False)
    lww_active = fields.Boolean(string='Recognition Entry Active', copy=False, default=False)

    def init(self):
        super().init()
        self.env.cr.execute("DROP INDEX IF EXISTS account_move_lww_unique_active")
        self.env.cr.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS account_move_lww_unique_active_product
            ON account_move (lww_picking_id, lww_entry_type, COALESCE(lww_product_id, 0))
            WHERE lww_active AND lww_entry_type IN ('reclass', 'backdated')
        """)

    def _lww_touched_projects(self):
        moves = self.filtered(lambda m: m.move_type == 'out_invoice')
        if not moves:
            return self.env['project.project']
        keys = set()
        for line in moves.invoice_line_ids:
            for key in (line.analytic_distribution or {}):
                keys.update(int(k) for k in key.split(',') if k)
        if not keys:
            return self.env['project.project']
        return self.env['project.project'].sudo().search([('account_id', 'in', list(keys))])

    def _post(self, soft=True):
        res = super()._post(soft=soft)
        self._lww_touched_projects()._lww_refresh_auto()
        return res

    def button_draft(self):
        res = super().button_draft()
        self._lww_touched_projects()._lww_refresh_auto()
        return res

    def button_cancel(self):
        res = super().button_cancel()
        self._lww_touched_projects()._lww_refresh_auto()
        return res
