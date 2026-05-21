from odoo import fields, models

class ProjectProject(models.Model):
    _inherit = 'project.project'

    sale_order_count = fields.Integer(
        groups='sales_team.group_sale_salesman,sale_readonly_access.group_sale_readonly',
    )
    sale_order_line_count = fields.Integer(
        groups='sales_team.group_sale_salesman,sale_readonly_access.group_sale_readonly',
    )