from odoo import models, fields, api

class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    @api.model
    def web_read_group(self, domain, fields, groupby, limit=None, offset=0, orderby=False, lazy=True):
        """Override web_read_group to filter out groups with zero total amount"""
        
        context = self.env.context
        if context.get('filter_zero_amount_projects') and groupby and 'account_id' in groupby[0]:
            # Get the grouped data first
            result = super().web_read_group(domain, fields, groupby, limit, offset, orderby, lazy)
            
            # Filter out groups where amount sum is 0
            if isinstance(result, dict) and 'groups' in result:
                filtered_groups = [
                    group for group in result['groups'] 
                    if group.get('amount', 0) != 0
                ]
                result['groups'] = filtered_groups
                result['length'] = len(filtered_groups)
            elif isinstance(result, list):
                # If result is a list of groups directly
                result = [
                    group for group in result 
                    if group.get('amount', 0) != 0
                ]
            
            return result
        
        return super().web_read_group(domain, fields, groupby, limit, offset, orderby, lazy)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        """Override search_read to filter out individual records from zero-total projects when grouped"""
        
        context = self.env.context
        if context.get('filter_zero_amount_projects') and context.get('group_by') == ['account_id']:
            if domain is None:
                domain = []
            
            # First, get all project totals
            all_records = self.search_read(
                [d for d in domain if d[0] != 'account_id'], 
                ['account_id', 'amount'], 
                0, None, None
            )
            
            # Calculate project totals
            project_totals = {}
            for record in all_records:
                account_id = record['account_id'][0] if record['account_id'] else False
                if account_id:
                    if account_id not in project_totals:
                        project_totals[account_id] = 0
                    project_totals[account_id] += record['amount']
            
            # Get projects with non-zero totals
            non_zero_projects = [
                project_id for project_id, total in project_totals.items() 
                if total != 0
            ]
            
            # Add filter for non-zero projects
            if non_zero_projects:
                domain = [d for d in domain if d[0] != 'account_id']  # Remove existing account_id filters
                domain.append(('account_id', 'in', non_zero_projects))
            else:
                # No projects with non-zero amounts, return empty
                domain.append(('id', 'in', []))
        
        return super().search_read(domain, fields, offset, limit, order)