from odoo import models, api, tools

ALWAYS_ALLOWED = {
    'base',
    'base_setup',
    'base_import',
    'web',
    'web_tour',
    'mail',
    'bus',
    'digest',
    'iap',
}


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    @api.model
    @tools.ormcache_context('self._uid', 'debug', keys=('lang', 'allowed_company_ids'))
    def load_menus(self, debug):
        return super().load_menus(debug)

    @api.model
    def _load_menus_blacklist(self):
        blacklist = super()._load_menus_blacklist()
        company = self.env.company

        if not company.restrict_modules or not company.allowed_modules:
            return blacklist

        allowed_set = ALWAYS_ALLOWED | {
            m.strip()
            for m in company.allowed_modules.split(',')
            if m.strip()
        }

        all_menu_ids = self.search([]).ids
        menu_module_map = self._get_menu_module_map(all_menu_ids)

        restricted = [
            menu_id for menu_id in all_menu_ids
            if menu_module_map.get(menu_id, 'base') not in allowed_set
        ]

        return list(set(blacklist + restricted))

    @api.model
    def _get_menu_module_map(self, menu_ids):
        if not menu_ids:
            return {}

        xid_records = self.env['ir.model.data'].sudo().search_read(
            [('model', '=', 'ir.ui.menu'), ('res_id', 'in', list(menu_ids))],
            ['res_id', 'module'],
        )

        menu_module_map = {}
        for rec in xid_records:
            menu_module_map[rec['res_id']] = rec['module']

        for menu_id in menu_ids:
            if menu_id not in menu_module_map:
                menu_module_map[menu_id] = 'base'

        return menu_module_map
