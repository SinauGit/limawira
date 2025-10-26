from odoo import api, fields, models, _
from odoo.exceptions import UserError
import base64
import json


class UserGroupTransferWizard(models.TransientModel):
    _name = "user.group.transfer.wizard"
    _description = "Export/Import User Membership & Groups (by XML ID)"

    # ------------------- Common -------------------
    mode = fields.Selection([
        ("export", "Export"),
        ("import", "Import"),
    ], required=True, default="export")

    scope = fields.Selection([
        ("user", "User Membership"),
        ("group", "Groups"),
    ], required=True, default="user")

    # scope=user
    user_ids = fields.Many2many("res.users", string="Users (optional)")
    include_inactive = fields.Boolean(string="Sertakan user inactive", default=False)

    # scope=group
    group_ids = fields.Many2many("res.groups", string="Groups (optional)")

    # export / import files
    export_file = fields.Binary(readonly=True)
    export_filename = fields.Char(readonly=True)
    import_file = fields.Binary(string="File JSON untuk Import")
    import_filename = fields.Char()

    # ------------------- Helpers -------------------
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

    # ------------------- EXPORT -------------------
    def action_export(self):
        self.ensure_one()
        if self.scope == "user":
            return self._export_user_membership()
        else:
            return self._export_groups()

    def _export_user_membership(self):
        domain = []
        if not self.include_inactive:
            domain.append(("active", "=", True))
        if self.user_ids:
            domain.append(("id", "in", self.user_ids.ids))
        users = self.env["res.users"].sudo().search(domain)

        payload = {"type": "user_membership", "items": []}
        for u in users:
            g_ok, g_missing = self._split_external_ids(u.groups_id)
            payload["items"].append({
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

    def _export_groups(self):
        """Export definisi group + relasinya (implied, menus, views, access, rules)."""
        domain = []
        if self.group_ids:
            domain.append(("id", "in", self.group_ids.ids))
        Group = self.env["res.groups"].sudo()
        groups = Group.search(domain) if domain else Group.search([])

        Menu = self.env["ir.ui.menu"].sudo()
        View = self.env["ir.ui.view"].sudo()
        Acc = self.env["ir.model.access"].sudo()
        Rule = self.env["ir.rule"].sudo()

        payload = {"type": "groups", "items": []}

        def _xid(rec):
            if not rec:
                return None
            return rec.get_external_id().get(rec.id)

        for g in groups:
            # xmlid group
            g_xid = _xid(g)

            # category
            cat = g.category_id
            cat_xid = _xid(cat)

            # implied groups (inherited)
            imp_ok, imp_missing = self._split_external_ids(g.implied_ids)

            # menus yg membatasi group (menu dengan groups_id berisi group ini)
            menus = Menu.search([("groups_id", "in", g.id)])
            menus_xids = []
            menus_fallback = []
            for m in menus:
                mx = _xid(m)
                if mx:
                    menus_xids.append(mx)
                else:
                    menus_fallback.append({
                        "name": m.name,
                        "complete_name": getattr(m, "complete_name", None),
                    })

            # views yg membatasi group
            views = View.search([("groups_id", "in", g.id)])
            views_xids = []
            views_fallback = []
            for v in views:
                vx = _xid(v)
                if vx:
                    views_xids.append(vx)
                else:
                    views_fallback.append({
                        "name": v.name,
                        "model": v.model,
                        "type": v.type,  # qweb, list(tree), form, search, kanban, ...
                    })

            # access rights milik group ini
            accs = Acc.search([("group_id", "=", g.id)])
            acc_items = []
            for a in accs:
                ax = _xid(a)
                acc_items.append({
                    "xmlid": ax,
                    "name": a.name,
                    "model": a.model_id.model,  # nama teknis model
                    "perm_read": a.perm_read,
                    "perm_write": a.perm_write,
                    "perm_create": a.perm_create,
                    "perm_unlink": a.perm_unlink,
                })

            # record rules yg mengikutsertakan group ini
            rules = Rule.search([("groups", "in", g.id)])
            rule_items = []
            for r in rules:
                rx = _xid(r)
                r_is_global = getattr(r, "global", getattr(r, "global_", False))
                rule_items.append({
                    "xmlid": rx,
                    "name": r.name,
                    "model": r.model_id.model,
                    "domain": r.domain_force or "[]",
                    "active": bool(r.active),
                    "global": bool(r_is_global),
                    "perm_read": bool(r.perm_read),
                    "perm_write": bool(r.perm_write),
                    "perm_create": bool(r.perm_create),
                    "perm_unlink": bool(r.perm_unlink),
                })

            payload["items"].append({
                "group_xmlid": g_xid,                       # boleh None
                "name": g.name,
                "category_xmlid": cat_xid,                  # boleh None
                "category_name_fallback": cat.name if (cat and not cat_xid) else None,
                "share": bool(getattr(g, "share", False)),

                # inherited (implied)
                "implied_groups_xmlids": [x for x in (i[1] for i in imp_ok) if x],
                "implied_groups_fallback": [
                    {"name": ig.name,
                     "category": ig.category_id.name if ig.category_id else None}
                    for ig in imp_missing
                ],

                # menus / views / access / rules
                "menus_xmlids": menus_xids,
                "menus_fallback": menus_fallback,
                "views_xmlids": views_xids,
                "views_fallback": views_fallback,
                "access_rights": acc_items,
                "record_rules": rule_items,
            })

        data = json.dumps(payload, indent=2).encode("utf-8")
        self.export_file = base64.b64encode(data)
        self.export_filename = "groups_export.json"
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "view_mode": "form",
            "res_id": self.id,
            "target": "new",
        }

    # ------------------- IMPORT -------------------
    def action_import(self):
        self.ensure_one()
        if not self.import_file:
            raise UserError(_("Unggah file JSON terlebih dahulu."))
        raw = base64.b64decode(self.import_file)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except Exception as e:
            raise UserError(_("File bukan JSON valid: %s") % e)

        ptype = payload.get("type")
        items = payload.get("items", [])
        if ptype == "groups" or self.scope == "group":
            return self._import_groups(items)
        else:
            return self._import_user_membership(items)

    def _import_user_membership(self, items):
        """Import mapping User ↔ Groups.
        Perubahan: jika user (login) tidak ditemukan, buat user baru otomatis.
        - Dibuat dengan name/login dari payload, active=True
        - Email diisi jika login terlihat seperti email
        - Groups:
            * Jika payload hasil resolving punya grup → set persis (replace)
            * Jika kosong → fallback set Internal User (base.group_user) bila tersedia
        """
        User = self.env["res.users"].sudo()
        Group = self.env["res.groups"].sudo()

        errors = []
        created = 0
        updated = 0

        internal_group = self.env.ref("base.group_user", raise_if_not_found=False)

        for row in items:
            login = row.get("login")
            if not login:
                errors.append("Row tanpa login.")
                continue

            # 1) Resolve target groups dari payload (XML ID → id, lalu fallback by name bila unik)
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

            # 2) Cari user; jika tidak ada → buat
            user = User.search([("login", "=", login)], limit=1)
            if not user:
                vals = {
                    "name": row.get("name") or login,
                    "login": login,
                    "active": True,
                }
                # isi email jika login tampak seperti email
                if "@" in login and "." in login.split("@")[-1]:
                    vals["email"] = login

                # set groups saat create:
                if target_groups:
                    vals["groups_id"] = [(6, 0, list(target_groups))]
                elif internal_group:
                    # fallback minimal agar user bisa akses backend
                    vals["groups_id"] = [(6, 0, [internal_group.id])]

                try:
                    user = User.create(vals)
                    created += 1
                except Exception as e:
                    errors.append(f"User '{login}' gagal dibuat: {e}")
                    continue
            else:
                # user sudah ada → update groups bila ada target
                if target_groups:
                    user.write({"groups_id": [(6, 0, list(target_groups))]})
                updated += 1

        msg = _("Import selesai. Dibuat: %s, Diupdate: %s.") % (created, updated)
        if errors:
            msg += "\n" + _("Catatan:") + "\n- " + "\n- ".join(errors[:30])

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


    def _import_groups(self, items):
        """Import groups + sinkron relasi: implied, menus, views, access rights, record rules.
        Perubahan: implied/inherited groups yang tidak ada akan DIBUAT otomatis.
        """
        Group = self.env["res.groups"].sudo()
        Category = self.env["ir.module.category"].sudo()
        Menu = self.env["ir.ui.menu"].sudo()
        View = self.env["ir.ui.view"].sudo()
        Acc = self.env["ir.model.access"].sudo()
        Rule = self.env["ir.rule"].sudo()
        IMD = self.env["ir.model.data"].sudo()
        IrModel = self.env["ir.model"].sudo()

        errors, created, updated = [], 0, 0

        def _xid(rec):
            return rec.get_external_id().get(rec.id) if rec else None

        def _ref(xid, expected_model):
            if not xid:
                return None
            rec = self.env.ref(xid, raise_if_not_found=False)
            if rec and rec._name == expected_model:
                return rec
            return None

        def _resolve_category(row):
            cat = _ref(row.get("category_xmlid"), "ir.module.category")
            if cat:
                return cat
            cname = row.get("category_name_fallback")
            if cname:
                cand = Category.search([("name", "=", cname)], limit=2)
                if len(cand) == 1:
                    return cand
                if len(cand) > 1:
                    errors.append(f"[{row.get('name')}] Nama category '{cname}' tidak unik.")
                else:
                    # buat category baru jika belum ada
                    return Category.create({"name": cname, "sequence": 10})
            return None

        def _resolve_group_by_name_cat(name, cat):
            dom = [("name", "=", name)]
            if cat:
                dom.append(("category_id", "=", cat.id))
            return Group.search(dom, limit=1)

        def _create_group(name, cat, gxid=None):
            g = Group.create({"name": name, "category_id": cat.id if cat else False})
            # daftarkan XML ID jika diberikan & belum dipakai
            if gxid and "." in gxid and not _ref(gxid, "res.groups"):
                module, namex = gxid.split(".", 1)
                exist_imd = IMD.search([("module", "=", module), ("name", "=", namex)], limit=1)
                if not exist_imd:
                    IMD.create({
                        "module": module,
                        "name": namex,
                        "model": "res.groups",
                        "res_id": g.id,
                        "noupdate": True,
                    })
            return g

        def _resolve_implied_ids(row, default_cat):
            """Kembalikan daftar id implied groups.
            - Jika XML ID tidak ketemu → buat group baru pakai nama tebak dari XML ID + default_cat.
            - Jika fallback (name/category) tidak ketemu → buat group baru sesuai fallback.
            """
            target_ids = set()

            # via XML ID
            for xid in (row.get("implied_groups_xmlids") or []):
                ref = _ref(xid, "res.groups")
                if ref:
                    target_ids.add(ref.id)
                else:
                    # buat group dari XML ID (nama tebak & category default)
                    try:
                        name_guess = xid.split(".", 1)[1] if "." in xid else xid
                        name_guess = name_guess.replace("_", " ").title()
                        g = _create_group(name_guess, default_cat, gxid=xid)
                        target_ids.add(g.id)
                    except Exception as e:
                        errors.append(f"[{row.get('name')}] Gagal membuat implied group dari XML ID '{xid}': {e}")

            # via fallback (name + category)
            for item in (row.get("implied_groups_fallback") or []):
                iname = item.get("name")
                icat_name = item.get("category")
                if not iname:
                    continue
                icat = None
                if icat_name:
                    icat = Category.search([("name", "=", icat_name)], limit=1)
                    if not icat:
                        icat = Category.create({"name": icat_name, "sequence": 10})
                else:
                    icat = default_cat

                cand = _resolve_group_by_name_cat(iname, icat)
                if cand:
                    target_ids.add(cand.id)
                else:
                    try:
                        g = _create_group(iname, icat)
                        target_ids.add(g.id)
                    except Exception as e:
                        errors.append(f"[{row.get('name')}] Gagal membuat implied group '{iname}': {e}")

            return list(target_ids)

        def _resolve_menus(row):
            want = set()
            for xid in (row.get("menus_xmlids") or []):
                ref = _ref(xid, "ir.ui.menu")
                if ref:
                    want.add(ref.id)
                else:
                    errors.append(f"[{row.get('name')}] XML ID menu '{xid}' tidak ditemukan.")
            for item in (row.get("menus_fallback") or []):
                mname = item.get("name")
                if not mname:
                    continue
                cand = Menu.search([("name", "=", mname)])
                if len(cand) == 1:
                    want.add(cand.id)
                else:
                    errors.append(f"[{row.get('name')}] Menu '{mname}' ambigu/tidak ditemukan.")
            return list(want)

        def _resolve_views(row):
            want = set()
            for xid in (row.get("views_xmlids") or []):
                ref = _ref(xid, "ir.ui.view")
                if ref:
                    want.add(ref.id)
                else:
                    errors.append(f"[{row.get('name')}] XML ID view '{xid}' tidak ditemukan.")
            for item in (row.get("views_fallback") or []):
                vname = item.get("name")
                vmodel = item.get("model")
                vtype = item.get("type")
                dom = []
                if vname:
                    dom.append(("name", "=", vname))
                if vmodel:
                    dom.append(("model", "=", vmodel))
                if vtype:
                    dom.append(("type", "=", vtype))
                if dom:
                    cand = View.search(dom)
                    if len(cand) == 1:
                        want.add(cand.id)
                    else:
                        errors.append(f"[{row.get('name')}] View fallback '{vname}/{vmodel}/{vtype}' ambigu/tidak ditemukan.")
            return list(want)

        def _upsert_access(group, acc_list):
            """Sinkron akses model untuk group:
            - Upsert semua item di acc_list
            - Hapus akses lain milik group yang tidak ada di acc_list
            """
            wanted_models = set()
            for it in (acc_list or []):
                model_code = it.get("model")
                if not model_code:
                    errors.append(f"[{group.name}] Access tanpa model, dilewati.")
                    continue
                m = IrModel.search([("model", "=", model_code)], limit=1)
                if not m:
                    errors.append(f"[{group.name}] Model '{model_code}' tidak ditemukan untuk access.")
                    continue
                wanted_models.add(m.id)

                rec = Acc.search([("group_id", "=", group.id), ("model_id", "=", m.id)], limit=1)
                vals = {
                    "name": it.get("name") or f"{group.name} / {model_code}",
                    "model_id": m.id,
                    "group_id": group.id,
                    "perm_read": bool(it.get("perm_read", False)),
                    "perm_write": bool(it.get("perm_write", False)),
                    "perm_create": bool(it.get("perm_create", False)),
                    "perm_unlink": bool(it.get("perm_unlink", False)),
                }
                if rec:
                    rec.write(vals)
                else:
                    Acc.create(vals)

            # hapus yang tidak diinginkan lagi
            if wanted_models:
                extra = Acc.search([("group_id", "=", group.id), ("model_id", "not in", list(wanted_models))])
                if extra:
                    extra.unlink()

        def _sync_group_m2m(records, field_name, group_id, want_ids):
            """Tambahkan group_id ke M2M 'field_name' pada semua records di want_ids,
            dan lepaskan dari records lain yang saat ini terhubung tetapi tidak di want_ids."""
            # tambah ke wanted
            if want_ids:
                for rec in records.browse(want_ids):
                    rec.write({field_name: [(4, group_id)]})
            # lepas dari yang tidak diinginkan
            current = records.search([(field_name, "in", group_id)])
            for rec in current:
                if rec.id not in want_ids:
                    rec.write({field_name: [(3, group_id)]})

        def _upsert_rules(group, rule_list):
            """Sinkron keanggotaan group pada rule:
            - Buat/update rule (by xmlid atau name+model+domain), pastikan group termasuk.
            - Lepas group dari rule lain yang tidak ada di list.
            """
            want_rule_ids = set()

            for it in (rule_list or []):
                rx = it.get("xmlid")
                name = it.get("name")
                model_code = it.get("model")
                domain = it.get("domain") or "[]"

                # resolve model
                m = IrModel.search([("model", "=", model_code)], limit=1) if model_code else None
                if not m:
                    errors.append(f"[{group.name}] Rule '{name}' model '{model_code}' tidak ditemukan.")
                    continue

                # resolve by xmlid
                target = _ref(rx, "ir.rule") if rx else None

                # fallback: by name+model+domain
                if not target:
                    dom = [("name", "=", name), ("model_id", "=", m.id), ("domain_force", "=", domain)]
                    target = Rule.search(dom, limit=1)

                vals = {
                    "name": name or f"{group.name} / {model_code}",
                    "model_id": m.id,
                    "domain_force": domain,
                    "active": bool(it.get("active", True)),
                    "perm_read": bool(it.get("perm_read", True)),
                    "perm_write": bool(it.get("perm_write", True)),
                    "perm_create": bool(it.get("perm_create", True)),
                    "perm_unlink": bool(it.get("perm_unlink", True)),
                }
                # set field 'global' atau 'global_' sesuai yang tersedia
                if "global" in Rule._fields:
                    vals["global"] = bool(it.get("global", False))
                elif "global_" in Rule._fields:
                    vals["global_"] = bool(it.get("global", False))

                if target:
                    target.write(vals)
                else:
                    target = Rule.create(vals)
                    # daftarkan xmlid jika diberikan & belum dipakai
                    gxid = it.get("xmlid")
                    if gxid:
                        try:
                            if "." in gxid and not self.env.ref(gxid, raise_if_not_found=False):
                                module, namex = gxid.split(".", 1)
                                exist_imd = IMD.search([("module", "=", module), ("name", "=", namex)], limit=1)
                                if not exist_imd:
                                    IMD.create({
                                        "module": module,
                                        "name": namex,
                                        "model": "ir.rule",
                                        "res_id": target.id,
                                        "noupdate": True,
                                    })
                        except Exception as e:
                            errors.append(f"[{group.name}] Gagal daftar XML ID rule '{gxid}': {e}")

                # pastikan group ada di rule
                target.write({"groups": [(4, group.id)]})
                want_rule_ids.add(target.id)

            # Lepas group dari rule lain yang saat ini terkait namun tidak ada di export
            current = Rule.search([("groups", "in", group.id)])
            for r in current:
                if r.id not in want_rule_ids:
                    r.write({"groups": [(3, group.id)]})

        # === Proses per item group ===
        for row in items:
            gname = row.get("name")
            if not gname:
                errors.append("Row group tanpa name.")
                continue

            cat = _resolve_category(row)

            # cari/match group target
            target = _ref(row.get("group_xmlid"), "res.groups")
            if not target:
                target = _resolve_group_by_name_cat(gname, cat)

            vals = {
                "name": gname,
                "category_id": cat.id if cat else False,
                "share": bool(row.get("share", False)),
            }

            if target:
                target.write(vals)
                updated += 1
            else:
                target = _create_group(gname, cat, gxid=row.get("group_xmlid"))
                updated += 0
                created += 1

            # resolve & sync implied (gunakan category group target sebagai default)
            implied_ids = _resolve_implied_ids(row, target.category_id)
            if implied_ids is not None:
                target.write({"implied_ids": [(6, 0, implied_ids)]})

            # sync menus membership untuk group ini
            menu_ids = _resolve_menus(row)
            _sync_group_m2m(Menu, "groups_id", target.id, menu_ids)

            # sync views membership untuk group ini
            view_ids = _resolve_views(row)
            _sync_group_m2m(View, "groups_id", target.id, view_ids)

            # upsert access rights (replace per model untuk group ini)
            _upsert_access(target, row.get("access_rights"))

            # sync record rules membership + upsert rule (replace membership untuk group ini)
            _upsert_rules(target, row.get("record_rules"))

        msg = _("Import groups selesai. Dibuat: %s, Diupdate: %s.") % (created, updated)
        if errors:
            msg += "\n" + _("Catatan:") + "\n- " + "\n- ".join(errors[:30])
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {"title": _("Selesai"), "message": msg, "type": "success", "sticky": False,
                    "next": {"type": "ir.actions.act_window_close"}},
        }

