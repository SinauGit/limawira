from odoo import api, SUPERUSER_ID


def post_init_hook(env):
    readonly_group = env.ref('sale_readonly_access.group_sale_readonly')
    actions = env['ir.embedded.actions'].search([
        ('python_method', '=', 'action_view_sos'),
        ('parent_res_model', '=', 'project.project'),
    ])
    actions.write({'groups_ids': [(4, readonly_group.id)]})