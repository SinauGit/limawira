from odoo import models, fields, api, _


class ProjectAnalyticTransferConfig(models.TransientModel):
    _name = 'project.analytic.transfer.config'
    _description = 'Project Analytic Transfer Configuration'
    _inherit = 'res.config.settings'

    # Performance settings
    batch_size = fields.Integer(
        'Batch Size',
        default=100,
        help="Number of records to process in each batch. Lower values use less memory but take longer."
    )
    
    max_retry_attempts = fields.Integer(
        'Max Retry Attempts',
        default=3,
        help="Maximum number of retry attempts for failed transfers."
    )
    
    retry_delay = fields.Integer(
        'Retry Delay (seconds)',
        default=5,
        help="Delay in seconds between retry attempts."
    )
    
    # Safety settings
    enable_backup_before_transfer = fields.Boolean(
        'Enable Backup Before Transfer',
        default=False,
        help="Create automatic backup before executing large transfers (requires database permissions)."
    )
    
    require_confirmation_above = fields.Integer(
        'Require Extra Confirmation Above',
        default=1000,
        help="Require additional confirmation for transfers affecting more than this many records."
    )
    
    # Logging settings
    enable_detailed_logging = fields.Boolean(
        'Enable Detailed Logging',
        default=True,
        help="Log detailed information about each transfer operation."
    )
    
    log_retention_days = fields.Integer(
        'Log Retention (days)',
        default=90,
        help="Number of days to keep detailed transfer logs."
    )
    
    # Email settings
    enable_email_notifications = fields.Boolean(
        'Enable Email Notifications',
        default=False,
        help="Send email notifications when transfers are completed."
    )
    
    notification_template_id = fields.Many2one(
        'mail.template',
        'Notification Template',
        help="Email template to use for transfer notifications."
    )
    
    notify_user_ids = fields.Many2many(
        'res.users',
        'transfer_notification_users_rel',
        'config_id',
        'user_id',
        string='Users to Notify',
        help="Users who should receive transfer notifications."
    )

    @api.model
    def get_values(self):
        res = super(ProjectAnalyticTransferConfig, self).get_values()
        ICPSudo = self.env['ir.config_parameter'].sudo()
        
        res.update(
            batch_size=int(ICPSudo.get_param('project_analytic_transfer.batch_size', 100)),
            max_retry_attempts=int(ICPSudo.get_param('project_analytic_transfer.max_retry_attempts', 3)),
            retry_delay=int(ICPSudo.get_param('project_analytic_transfer.retry_delay', 5)),
            enable_backup_before_transfer=ICPSudo.get_param('project_analytic_transfer.enable_backup_before_transfer', False),
            require_confirmation_above=int(ICPSudo.get_param('project_analytic_transfer.require_confirmation_above', 1000)),
            enable_detailed_logging=ICPSudo.get_param('project_analytic_transfer.enable_detailed_logging', True),
            log_retention_days=int(ICPSudo.get_param('project_analytic_transfer.log_retention_days', 90)),
            enable_email_notifications=ICPSudo.get_param('project_analytic_transfer.enable_email_notifications', False),
            notification_template_id=int(ICPSudo.get_param('project_analytic_transfer.notification_template_id', 0)) or False,
        )
        
        # Handle Many2many field separately
        notify_user_ids = ICPSudo.get_param('project_analytic_transfer.notify_user_ids', '')
        if notify_user_ids:
            res['notify_user_ids'] = [(6, 0, [int(uid) for uid in notify_user_ids.split(',') if uid.isdigit()])]
        else:
            res['notify_user_ids'] = [(6, 0, [])]
            
        return res

    def set_values(self):
        super(ProjectAnalyticTransferConfig, self).set_values()
        ICPSudo = self.env['ir.config_parameter'].sudo()
        
        ICPSudo.set_param('project_analytic_transfer.batch_size', self.batch_size)
        ICPSudo.set_param('project_analytic_transfer.max_retry_attempts', self.max_retry_attempts)
        ICPSudo.set_param('project_analytic_transfer.retry_delay', self.retry_delay)
        ICPSudo.set_param('project_analytic_transfer.enable_backup_before_transfer', self.enable_backup_before_transfer)
        ICPSudo.set_param('project_analytic_transfer.require_confirmation_above', self.require_confirmation_above)
        ICPSudo.set_param('project_analytic_transfer.enable_detailed_logging', self.enable_detailed_logging)
        ICPSudo.set_param('project_analytic_transfer.log_retention_days', self.log_retention_days)
        ICPSudo.set_param('project_analytic_transfer.enable_email_notifications', self.enable_email_notifications)
        ICPSudo.set_param('project_analytic_transfer.notification_template_id', self.notification_template_id.id or 0)
        
        # Handle Many2many field separately
        user_ids = ','.join(str(uid) for uid in self.notify_user_ids.ids) if self.notify_user_ids else ''
        ICPSudo.set_param('project_analytic_transfer.notify_user_ids', user_ids)

    @api.model
    def get_batch_size(self):
        """Get configured batch size"""
        return int(self.env['ir.config_parameter'].sudo().get_param('project_analytic_transfer.batch_size', 100))
    
    @api.model
    def get_max_retry_attempts(self):
        """Get configured max retry attempts"""
        return int(self.env['ir.config_parameter'].sudo().get_param('project_analytic_transfer.max_retry_attempts', 3))
    
    @api.model
    def is_detailed_logging_enabled(self):
        """Check if detailed logging is enabled"""
        return self.env['ir.config_parameter'].sudo().get_param('project_analytic_transfer.enable_detailed_logging', 'True') == 'True'
    
    @api.model
    def is_email_notifications_enabled(self):
        """Check if email notifications are enabled"""
        return self.env['ir.config_parameter'].sudo().get_param('project_analytic_transfer.enable_email_notifications', 'False') == 'True'

    def execute(self):
        """Apply settings from this form.
        This matches the 'Apply Settings' button in the view to prevent missing-method errors.
        """
        self.ensure_one()
        self.set_values()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Transfer Settings'),
                'message': _('Settings have been applied.'),
                'type': 'success',
                'sticky': False,
            }
        }
