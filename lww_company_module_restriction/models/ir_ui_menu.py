from odoo import models, api

# Modules that must always be visible regardless of restriction
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
    def _visible_menu_ids(self, debug=False):
        all_visible = super()._visible_menu_ids(debug=debug)
        company = self.env.company

        if not company.restrict_modules or not company.allowed_modules:
            return all_visible

        allowed_set = ALWAYS_ALLOWED | {
            m.strip()
            for m in company.allowed_modules.split(',')
            if m.strip()
        }

        menu_module_map = self._get_menu_module_map(all_visible)

        filtered = [
            menu_id for menu_id in all_visible
            if menu_module_map.get(menu_id, 'base') in allowed_set
        ]

        return filtered

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

        # Menus not found in ir.model.data are custom/dynamic — allow them
        for menu_id in menu_ids:
            if menu_id not in menu_module_map:
                menu_module_map[menu_id] = 'base'

        return menu_module_map
