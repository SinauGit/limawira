from odoo import api, models, tools


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    @api.model
    @tools.ormcache('frozenset(self.env.user.groups_id.ids)', 'debug',
                    'self.env.company.id', cache='templates')
    def _visible_menu_ids(self, debug=False):
        visible = super()._visible_menu_ids(debug=debug)
        param = self.env['ir.config_parameter'].sudo().get_param(
            'menu_restrict_company.restricted_company_id', '0')
        try:
            restricted_id = int(param)
        except ValueError:
            restricted_id = 0
        if restricted_id and self.env.company.id == restricted_id:
            stock_root = self.env.ref('stock.menu_stock_root',
                                      raise_if_not_found=False)
            if stock_root:
                menus = self.browse(visible)
                allowed = menus.filtered(
                    lambda m: int(m.parent_path.split('/')[0]) == stock_root.id
                )
                visible = set(allowed.ids)
        return visible