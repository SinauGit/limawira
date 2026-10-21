from odoo import fields, models


class LwwRecognitionLog(models.Model):
    _name = 'lww.recognition.log'
    _description = 'Project Recognition Audit Log'
    _order = 'id desc'

    company_id = fields.Many2one('res.company', required=True, default=lambda s: s.env.company, index=True)
    project_id = fields.Many2one('project.project', index=True, ondelete='cascade')
    picking_id = fields.Many2one('stock.picking', index=True, ondelete='set null')
    action = fields.Selection([
        ('year_auto', 'Year Reached (Billing)'),
        ('year_override', 'Year Overridden'),
        ('date_update', 'Threshold Date Updated'),
        ('year_warning', 'Year Mismatch Warning'),
        ('recognized', 'Recognized'),
        ('pending', 'Set Pending'),
        ('journal', 'Journals Created'),
        ('reversal', 'Journals Reversed'),
        ('return', 'Return Processed'),
    ], required=True)
    old_year = fields.Integer()
    new_year = fields.Integer()
    user_id = fields.Many2one('res.users', default=lambda s: s.env.user, readonly=True)
    move_ids = fields.Many2many('account.move', string='Journals')
    note = fields.Char()
