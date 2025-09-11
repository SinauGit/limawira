from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


# =====================
# hr.expense
# =====================
class HrExpense(models.Model):
    _inherit = "hr.expense"


    # Restrict selection to own_account (replace base selection)
    payment_mode = fields.Selection(
        selection=[
            ("own_account", "Employee (to reimburse)"),
    ],
    default="own_account",
    tracking=True,
    )


    # Hide 'company_account' in all clients (fields_get used by views/form/rpc)
    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super().fields_get(allfields=allfields, attributes=attributes)
        fld = res.get("payment_mode")
        if fld and fld.get("selection"):
            fld["selection"] = [s for s in fld["selection"] if s[0] != "company_account"]
        return res


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals["payment_mode"] = "own_account"
        return super().create(vals_list)


    def write(self, vals):
        if "payment_mode" in vals and vals["payment_mode"] != "own_account":
            vals = dict(vals, payment_mode="own_account")
        return super().write(vals)


    @api.constrains("payment_mode")
    def _check_payment_mode(self):
        for rec in self:
            if rec.payment_mode and rec.payment_mode != "own_account":
                raise ValidationError(_("Penggunaan 'Company' pada Metode Pembayaran tidak diperbolehkan."))




# =====================
# hr.expense.sheet
# =====================
class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"


# Replace selection as well; keep compute from base if any (we do not override compute)
    payment_mode = fields.Selection(
        selection=[
            ("own_account", "Employee (to reimburse)"),
        ],
        default="own_account",
        tracking=True,
        )


    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super().fields_get(allfields=allfields, attributes=attributes)
        fld = res.get("payment_mode")
        if fld and fld.get("selection"):
            fld["selection"] = [s for s in fld["selection"] if s[0] != "company_account"]
        return res


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals["payment_mode"] = "own_account"
        return super().create(vals_list)


    def write(self, vals):
        if "payment_mode" in vals and vals["payment_mode"] != "own_account":
            vals = dict(vals, payment_mode="own_account")
        return super().write(vals)


    @api.constrains("payment_mode")
    def _check_payment_mode(self):
        for rec in self:
            if rec.payment_mode and rec.payment_mode != "own_account":
                raise ValidationError(_("Penggunaan 'Company' pada Metode Pembayaran tidak diperbolehkan."))




class EmployeeBase(models.AbstractModel):
    _inherit = 'hr.employee.base'

    # gunakan field helper standard yg sudah ada di core
    filter_for_expense = fields.Boolean(store=False, search='_search_filter_for_expense', groups="hr.group_hr_user")

    def _search_filter_for_expense(self, operator, value):
        # tetap patuh pada kontrak method bawaan
        assert operator == '=' and value, "Operation not supported"

        user = self.env.user

        # Longgarkan untuk Team Approver: samakan dengan Expense User/Accounting User
        if (
            user.has_groups('hr_expense.group_hr_expense_user')
            or user.has_groups('account.group_account_user')
            or user.has_groups('hr_expense.group_hr_expense_team_approver')  # kunci perubahan
        ):
            # semua employee dalam company aktif & turunannya (multi-company aware)
            return ['|', ('company_id', '=', False), ('company_id', 'child_of', self.env.company.root_id.id)]

        # fallback: employee biasa -> hanya dirinya sendiri (aman)
        emp = user.employee_id
        if emp:
            return [
                ('id', '=', emp.id),
                '|', ('company_id', '=', False),
                ('company_id', '=', emp.company_id.id),
            ]
        # jika user tak terhubung ke employee
        return [('id', '=', 0)]