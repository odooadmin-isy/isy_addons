# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PortalAcknowledgmentSubmission(models.Model):
    _name = 'portal.acknowledgment.submission'
    _description = 'Portal Acknowledgment Submission'
    _order = 'submit_date desc, id desc'
    _inherit = ['mail.thread']

    campaign_id = fields.Many2one(
        'portal.acknowledgment.campaign',
        string='Campaign',
        required=True,
        ondelete='restrict',
        index=True,
    )
    employee_id = fields.Many2one('hr.employee', required=True, index=True)
    user_id = fields.Many2one('res.users', required=True, index=True)
    manager_id = fields.Many2one(
        'hr.employee',
        string='Manager',
        compute='_compute_manager_id',
        store=True,
    )
    tab1_acknowledged = fields.Boolean(string='Tab 1 Acknowledged')
    tab2_acknowledged = fields.Boolean(string='Tab 2 Acknowledged')
    tab3_acknowledged = fields.Boolean(string='Tab 3 Acknowledged')
    submit_date = fields.Datetime(string='Submitted On', readonly=True)
    state = fields.Selection(
        [('submitted', 'Submitted')],
        default='submitted',
        required=True,
    )

    _sql_constraints = [
        (
            'campaign_user_unique',
            'unique(campaign_id, user_id)',
            'You have already submitted this acknowledgment.',
        ),
    ]

    @api.depends('employee_id', 'employee_id.parent_id')
    def _compute_manager_id(self):
        for submission in self:
            submission.manager_id = submission.employee_id.parent_id

    @api.model
    def _get_employee_for_user(self, user):
        employee = self.env['hr.employee'].sudo().search([
            ('user_id', '=', user.id),
        ], limit=1)
        if not employee:
            employee = self.env['hr.employee'].sudo().search([
                ('work_email', '=', user.email),
            ], limit=1)
        return employee

    def _get_notification_recipients(self):
        self.ensure_one()
        email_to = []
        email_cc = []
        manager = self.manager_id
        if manager and manager.work_email:
            email_to.append(manager.work_email)
        for coordinator in self.campaign_id.communication_coordinator_ids:
            if coordinator.work_email and coordinator.work_email not in email_to and coordinator.work_email not in email_cc:
                email_cc.append(coordinator.work_email)
        return {
            'email_to': ','.join(email_to),
            'email_cc': ','.join(email_cc),
        }

    def action_send_submission_email(self):
        self.ensure_one()
        template = self.env.ref(
            'portal_acknowledgment.mail_template_acknowledgment_submitted',
            raise_if_not_found=False,
        )
        if not template:
            return
        recipients = self._get_notification_recipients()
        if not recipients['email_to'] and not recipients['email_cc']:
            return
        template.with_context(
            notification_email_to=recipients['email_to'],
            notification_email_cc=recipients['email_cc'],
        ).send_mail(self.id, force_send=True)

    @api.model
    def submit_from_portal(self, campaign, user, tab1, tab2, tab3):
        if not all([tab1, tab2, tab3]):
            raise UserError(
                _('Please read all content, watch the video, and check all boxes before submitting.')
            )
        employee = self._get_employee_for_user(user)
        if not employee:
            raise UserError(
                _('No employee record is linked to your user account. '
                  'Please contact HR to link your employee profile.')
            )
        if not employee.is_new_employee_for_acknowledgment():
            raise UserError(
                _('This acknowledgment is only available for newly joined employees.')
            )
        existing = self.sudo().search([
            ('campaign_id', '=', campaign.id),
            ('user_id', '=', user.id),
        ], limit=1)
        if existing:
            raise UserError(_('You have already submitted this acknowledgment.'))

        submission = self.sudo().create({
            'campaign_id': campaign.id,
            'employee_id': employee.id,
            'user_id': user.id,
            'tab1_acknowledged': True,
            'tab2_acknowledged': True,
            'tab3_acknowledged': True,
            'submit_date': fields.Datetime.now(),
        })
        submission.action_send_submission_email()
        return submission
