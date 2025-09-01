from odoo import api, fields, models

class MailActivitySchedule(models.TransientModel):
    _inherit = "mail.activity.schedule"

    # Field pengganti untuk memilih banyak user
    multi_user_ids = fields.Many2many(
        "res.users",
        "mail_activity_schedule_multi_user_rel",
        "wizard_id",
        "user_id",
        string="Assigned to",
        help="Pilih lebih dari satu pengguna. Sistem akan membuat satu aktivitas untuk setiap pengguna.",
    )

    def _get_target_records(self):
        """Ambil record target dari wizard (aktif di context atau field res_model/res_id)."""
        self.ensure_one()
        model = self.res_model or self.env.context.get("active_model")
        if not model:
            return self.env[self.env.context.get("active_model", "res.partner")].browse([])
        ids = []
        if self.res_id:
            ids = [self.res_id]
        elif self.env.context.get("active_ids"):
            ids = self.env.context["active_ids"]
        return self.env[model].browse(ids)

    def _prepare_activity_vals(self, res_model, res_id, user):
        """Siapkan nilai minimal untuk membuat mail.activity."""
        self.ensure_one()
        return {
            "res_model": res_model,
            "res_id": res_id,
            "activity_type_id": self.activity_type_id.id,
            "user_id": user.id,
            "summary": self.summary,
            "note": self.note,
            "date_deadline": self.date_deadline,
        }

    def action_schedule(self):
        """
        Override: jika multi_user_ids diisi, jadikan satu activity per user.
        Jika kosong, tetap pakai activity_user_id standar.
        """
        for wiz in self:
            records = wiz._get_target_records()
            users = wiz.multi_user_ids
            if not users:
                # fallback ke single assigned (field standar wizard)
                users = wiz.activity_user_id and wiz.activity_user_id.sudo()
                users = users and users or self.env.user
            for rec in records:
                if isinstance(users, models.BaseModel) and users._name == "res.users":
                    # single
                    vals = wiz._prepare_activity_vals(rec._name, rec.id, users)
                    self.env["mail.activity"].create(vals)
                else:
                    # multiple
                    for user in users:
                        vals = wiz._prepare_activity_vals(rec._name, rec.id, user)
                        self.env["mail.activity"].create(vals)
        # Tutup wizard
        return {"type": "ir.actions.act_window_close"}
