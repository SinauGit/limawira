from odoo import api, fields, models, _
from odoo.exceptions import UserError
import base64
import json

class UserGroupTransferWizard(models.TransientModel):
    _name = "user.group.transfer.wizard"
    _description = "Export/Import User ↔ Groups (by XML ID)"

    mode = fields.Selection([
        ("export", "Export"),
        ("import", "Import"),
    ], required=True, default="export")

    user_ids = fields.Many2many("res.users", string="Users (optional)")
    include_inactive = fields.Boolean(string="Sertakan user inactive", default=False)

    export_file = fields.Binary(readonly=True)
    export_filename = fields.Char(readonly=True)

    import_file = fields.Binary(string="File JSON untuk Import")
    import_filename = fields.Char()

    # ---------- Helpers ----------
    def _split_external_ids(self, records):
        """Pisahkan records menjadi (punya_xmlid, tanpa_xmlid) dan ambil xmlid per record."""
        xmlids = records.get_external_id()  # {id: 'module.name' or False}
        ok, missing = [], []
        for r in records:
            xid = xmlids.get(r.id)
            if xid:
                ok.append((r, xid))
            else:
                missing.append(r)
        return ok, missing

    # ---------- Export ----------
    def action_export(self):
        self.ensure_one()
        domain = []
        if not self.include_inactive:
            domain.append(("active", "=", True))
        if self.user_ids:
            domain.append(("id", "in", self.user_ids.ids))
        users = self.env["res.users"].sudo().search(domain)

        payload = []
        for u in users:
            g_ok, g_missing = self._split_external_ids(u.groups_id)
            payload.append({
                "login": u.login,
                "name": u.name,
                "groups_xmlids": [xid for (_g, xid) in g_ok],
                "groups_names_fallback": [g.name for g in g_missing] if g_missing else [],
            })

        data = json.dumps(payload, indent=2).encode("utf-8")
        self.export_file = base64.b64encode(data)
        self.export_filename = "user_groups_export.json"
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "view_mode": "form",
            "res_id": self.id,
            "target": "new",
        }

    # ---------- Import ----------
    def action_import(self):
        self.ensure_one()
        if not self.import_file:
            raise UserError(_("Unggah file JSON terlebih dahulu."))
        raw = base64.b64decode(self.import_file)
        try:
            rows = json.loads(raw.decode("utf-8"))
        except Exception as e:
            raise UserError(_("File bukan JSON valid: %s") % e)

        User = self.env["res.users"].sudo()
        Group = self.env["res.groups"].sudo()

        errors = []
        applied = 0

        for row in rows:
            login = row.get("login")
            if not login:
                errors.append("Row tanpa login.")
                continue

            user = User.search([("login", "=", login)], limit=1)
            if not user:
                errors.append(f"User '{login}' tidak ditemukan di DB target.")
                continue

            # -------- Resolve GROUPS saja --------
            target_groups = set()

            for xid in (row.get("groups_xmlids") or []):
                ref = self.env.ref(xid, raise_if_not_found=False)
                if ref and ref._name == "res.groups":
                    target_groups.add(ref.id)
                else:
                    errors.append(f"[{login}] XML ID grup '{xid}' tidak ditemukan.")

            for gname in (row.get("groups_names_fallback") or []):
                if not gname:
                    continue
                cand = Group.search([("name", "=", gname)])
                if len(cand) == 1:
                    target_groups.add(cand.id)
                elif len(cand) > 1:
                    errors.append(f"[{login}] Nama grup '{gname}' tidak unik, lewati.")
                else:
                    errors.append(f"[{login}] Grup nama '{gname}' tidak ditemukan.")

            if target_groups:
                user.write({"groups_id": [(6, 0, list(target_groups))]})
                applied += 1
            else:
                errors.append(f"[{login}] Tidak ada grup valid untuk di-set.")

        msg = _("%s user berhasil di-update.") % applied
        if errors:
            tail = "\n- " + "\n- ".join(errors[:30])  # batasi tampilan
            msg = f"{msg}\n{_('Catatan:')}{tail}"

        # Notifikasi + tutup wizard (kompatibel 18)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Import selesai"),
                "message": msg,
                "type": "success",
                "sticky": False,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
