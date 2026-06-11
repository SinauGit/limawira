import json
from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.home import Home


class HomeRestricted(Home):

    @http.route('/web/webclient/load_menus/<string:unique>', type='http', auth='user', methods=['GET'], readonly=True)
    def web_load_menus(self, unique, lang=None):
        if lang:
            request.update_context(lang=lang)

        menus = request.env['ir.ui.menu'].load_web_menus(request.session.debug)

        # Ambil company aktif dari session
        company_id = request.session.get('company_id') or request.env.company.id
        company = request.env['res.company'].browse(company_id)

        if company.exists() and company.restrict_modules and company.allowed_modules:
            restricted_ids = request.env['ir.ui.menu'].get_restricted_menu_ids(company)

            if restricted_ids:
                # Hapus menu yang ter-restrict dari hasil load_web_menus
                menus = {
                    k: v for k, v in menus.items()
                    if k == 'root' or (isinstance(k, int) and k not in restricted_ids)
                }
                # Bersihkan children yang sudah dihapus
                for menu in menus.values():
                    if 'children' in menu:
                        menu['children'] = [
                            c for c in menu['children']
                            if c in menus
                        ]
                # Hapus root apps yang sudah tidak punya children dan tidak punya action
                to_remove = set()
                for k, v in menus.items():
                    if k == 'root':
                        continue
                    if not v.get('children') and not v.get('actionID'):
                        to_remove.add(k)
                menus = {k: v for k, v in menus.items() if k not in to_remove}
                # Bersihkan children root dari app yang sudah dihapus
                if 'root' in menus:
                    menus['root']['children'] = [
                        c for c in menus['root']['children']
                        if c in menus
                    ]

        body = json.dumps(menus)
        response = request.make_response(body, [
            ('Content-Type', 'application/json'),
            ('Cache-Control', 'no-cache, no-store, must-revalidate'),
        ])
        return response
