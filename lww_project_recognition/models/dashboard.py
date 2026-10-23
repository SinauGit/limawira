from odoo import api, fields, models


class LwwRecognitionDashboard(models.TransientModel):
    _name = 'lww.recognition.dashboard'
    _description = 'Project Recognition Dashboard'

    awaiting_count = fields.Integer(compute='_compute_counts')
    pending_count = fields.Integer(compute='_compute_counts')
    recognized_count = fields.Integer(compute='_compute_counts')
    no_year_count = fields.Integer(compute='_compute_counts')
    near_count = fields.Integer(compute='_compute_counts')
    override_count = fields.Integer(compute='_compute_counts')
    journal_count = fields.Integer(compute='_compute_counts')

    def _compute_display_name(self):
        for rec in self:
            rec.display_name = 'Project DO Recognition Management Dashboard'

    def _company_ids(self):
        return self.env.companies.ids

    def _pickings(self, statuses):
        return self.env['stock.picking'].sudo().search([
            ('company_id', 'in', self._company_ids()), ('x_accounting_status', 'in', statuses)])

    def _no_year_projects(self):
        return self._pickings(['awaiting']).x_project_id.filtered(lambda p: not p.lww_rec_year)

    def _near_projects(self):
        projects = self.env['project.project'].sudo().search([
            ('company_id', 'in', self._company_ids()), ('lww_rec_year', '=', 0),
            ('lww_sale_order_id', '!=', False)])
        res = self.env['project.project']
        for project in projects:
            config = self.env['lww.recognition.config']._get(project.company_id)
            if config and 70.0 <= project.lww_progress < config.threshold:
                res |= project
        return res

    def _override_projects(self):
        return self.env['project.project'].sudo().search([
            ('company_id', 'in', self._company_ids()), ('lww_manual_override', '=', True)])

    def _journals(self):
        return self.env['account.move'].sudo().search([
            ('company_id', 'in', self._company_ids()), ('lww_active', '=', True),
            ('lww_entry_type', 'in', ('reclass', 'backdated'))])

    def _compute_counts(self):
        for rec in self:
            rec.awaiting_count = len(rec._pickings(['awaiting']))
            rec.pending_count = len(rec._pickings(['pending']))
            rec.recognized_count = len(rec._pickings(['recognized', 'returned']))
            rec.no_year_count = len(rec._no_year_projects())
            rec.near_count = len(rec._near_projects())
            rec.override_count = len(rec._override_projects())
            rec.journal_count = len(rec._journals())

    @api.model
    def action_open(self):
        rec = self.create({})
        return {'type': 'ir.actions.act_window', 'name': 'Project DO Recognition Management Dashboard', 'res_model': self._name,
                'res_id': rec.id, 'view_mode': 'form', 'target': 'current'}

    def _open(self, xmlid, ids, name):
        action = self.env['ir.actions.act_window']._for_xml_id(xmlid)
        action['domain'] = [('id', 'in', ids)]
        action['name'] = name
        return action

    def action_awaiting(self):
        return self._open('lww_project_recognition.lww_picking_dashboard_action',
                          self._pickings(['awaiting']).ids, 'Awaiting DO')

    def action_pending(self):
        return self._open('lww_project_recognition.lww_picking_dashboard_action',
                          self._pickings(['pending']).ids, 'Pending DO')

    def action_recognized(self):
        return self._open('lww_project_recognition.lww_picking_dashboard_action',
                          self._pickings(['recognized', 'returned']).ids, 'Recognized DO')

    def action_no_year(self):
        return self._open('lww_project_recognition.lww_project_dashboard_action',
                          self._no_year_projects().ids, 'Projects Without Year')

    def action_near(self):
        return self._open('lww_project_recognition.lww_project_dashboard_action',
                          self._near_projects().ids, 'Near Threshold')

    def action_override(self):
        return self._open('lww_project_recognition.lww_project_dashboard_action',
                          self._override_projects().ids, 'Manual Override')

    def action_journals(self):
        return self._open('lww_project_recognition.lww_recognition_move_action',
                          self._journals().ids, 'Active Recognition Journals')
