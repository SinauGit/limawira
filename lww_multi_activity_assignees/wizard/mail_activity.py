# -*- coding: utf-8 -*-
from odoo import api, fields, models

# =========================
# Wizard Schedule Activity
# =========================
class MailActivitySchedule(models.TransientModel):
    _inherit = 'mail.activity.schedule'

    multi_user_ids = fields.Many2many(
        'res.users', string='Assigned to (Multiple)',
        help='Pilih satu atau lebih pengguna. Sistem akan membuat satu aktivitas per pengguna.'
    )

    def _get_target_records(self):
        """Ambil record target dari context atau res_model/res_id wizard."""
        self.ensure_one()
        if self.res_model and self.res_id:
            return self.env[self.res_model].browse(self.res_id)
        am = self.env.context.get('active_model')
        aids = self.env.context.get('active_ids')
        return self.env[am].browse(aids) if am and aids else self.env[self.res_model]

    def _prepare_activity_vals(self, model, res_id, user):
        self.ensure_one()
        return {
            'res_model_id': self.env['ir.model']._get_id(model),
            'res_id': res_id,
            'activity_type_id': self.activity_type_id.id,
            'summary': self.summary,
            'note': self.note,
            'user_id': user.id,
            'date_deadline': self.date_deadline,
            'automated': False,
        }

    def action_schedule(self):
        """Buat aktivitas untuk setiap user yang dipilih pada setiap record target."""
        records = self._get_target_records()
        for wiz in self:
            # urutan prioritas assignee: multi → single → current user
            users = wiz.multi_user_ids or wiz.activity_user_id or self.env.user
            users = users.sudo()
            for rec in records:
                for user in users:
                    vals = wiz._prepare_activity_vals(rec._name, rec.id, user)
                    self.env['mail.activity'].create(vals)
        return {'type': 'ir.actions.act_window_close'}


# =========================
# mail.activity – info semua assignee untuk dokumen yang sama
# =========================
class MailActivity(models.Model):
    _inherit = 'mail.activity'

    all_assigned_user_ids = fields.Many2many(
        'res.users', string='All Assigned Users',
        compute='_compute_all_assigned_user_ids', store=False
    )

    def _compute_all_assigned_user_ids(self):
        if not self:
            return
        # Kelompokkan per dokumen agar hemat query
        doc_map = {}
        for act in self:
            key = (act.res_model, act.res_id)
            doc_map.setdefault(key, self.env['mail.activity'])
            doc_map[key] |= act
        for (model, rid), acts in doc_map.items():
            all_acts = self.env['mail.activity'].search([('res_model', '=', model), ('res_id', '=', rid)])
            users = all_acts.mapped('user_id')
            for act in acts:
                act.all_assigned_user_ids = users
# -*- coding: utf-8 -*-
from odoo import api, fields, models

# =========================
# Wizard Schedule Activity
# =========================
class MailActivitySchedule(models.TransientModel):
    _inherit = 'mail.activity.schedule'

    multi_user_ids = fields.Many2many(
        'res.users', string='Assigned to (Multiple)',
        help='Pilih satu atau lebih pengguna. Sistem akan membuat satu aktivitas per pengguna.'
    )

    def _get_target_records(self):
        """Ambil record target dari context atau res_model/res_id wizard."""
        self.ensure_one()
        if self.res_model and self.res_id:
            return self.env[self.res_model].browse(self.res_id)
        am = self.env.context.get('active_model')
        aids = self.env.context.get('active_ids')
        return self.env[am].browse(aids) if am and aids else self.env[self.res_model]

    def _prepare_activity_vals(self, model, res_id, user):
        self.ensure_one()
        return {
            'res_model_id': self.env['ir.model']._get_id(model),
            'res_id': res_id,
            'activity_type_id': self.activity_type_id.id,
            'summary': self.summary,
            'note': self.note,
            'user_id': user.id,
            'date_deadline': self.date_deadline,
            'automated': False,
        }

    def action_schedule(self):
        """Buat aktivitas untuk setiap user yang dipilih pada setiap record target."""
        records = self._get_target_records()
        for wiz in self:
            # urutan prioritas assignee: multi → single → current user
            users = wiz.multi_user_ids or wiz.activity_user_id or self.env.user
            users = users.sudo()
            for rec in records:
                for user in users:
                    vals = wiz._prepare_activity_vals(rec._name, rec.id, user)
                    self.env['mail.activity'].create(vals)
        return {'type': 'ir.actions.act_window_close'}


# =========================
# mail.activity – info semua assignee untuk dokumen yang sama
# =========================
class MailActivity(models.Model):
    _inherit = 'mail.activity'

    all_assigned_user_ids = fields.Many2many(
        'res.users', string='All Assigned Users',
        compute='_compute_all_assigned_user_ids', store=False
    )

    def _compute_all_assigned_user_ids(self):
        if not self:
            return
        # Kelompokkan per dokumen agar hemat query
        doc_map = {}
        for act in self:
            key = (act.res_model, act.res_id)
            doc_map.setdefault(key, self.env['mail.activity'])
            doc_map[key] |= act
        for (model, rid), acts in doc_map.items():
            all_acts = self.env['mail.activity'].search([('res_model', '=', model), ('res_id', '=', rid)])
            users = all_acts.mapped('user_id')
            for act in acts:
                act.all_assigned_user_ids = users
