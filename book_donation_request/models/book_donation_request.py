# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class BookDonationRequest(models.Model):
    _name = 'book.donation.request'
    _description = 'Book Donation Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'request_date desc, id desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
    )
    librarian_id = fields.Many2one(
        'res.users',
        string='Librarian',
        required=True,
        default=lambda self: self.env.user,
        tracking=True,
        index=True,
        readonly=True,
    )
    request_date = fields.Date(
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    donated_to_id = fields.Many2one('isy.donated.to', string='Donated To', tracking=True)
    donation_expected_date = fields.Date(string='Expected Donation Date')
    notes = fields.Html()
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('first_approval', 'Waiting First Approval'),
            ('second_approval', 'Waiting Second Approval'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('cancelled', 'Cancelled'),
        ],
        string='Status',
        default='draft',
        required=True,
        tracking=True,
        copy=False,
    )
    first_approver_id = fields.Many2one(
        'res.users',
        string='First Approver',
        tracking=True,
        domain="[('share', '=', False)]",
    )
    second_approver_id = fields.Many2one(
        'res.users',
        string='Second Approver',
        tracking=True,
        domain="[('share', '=', False)]",
    )
    first_approval_date = fields.Datetime(readonly=True)
    second_approval_date = fields.Datetime(readonly=True)
    rejection_reason = fields.Text(tracking=True)
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        required=True,
        readonly=True,
    )
    attachment_1 = fields.Binary(string="Attachment 1", attachment=True)
    attachment_1_filename = fields.Char(string="Attachment 1 Filename")
    attachment_2 = fields.Binary(string="Attachment 2", attachment=True)
    attachment_2_filename = fields.Char(string="Attachment 2 Filename")
    attachment_3 = fields.Binary(string="Attachment 3", attachment=True)
    attachment_3_filename = fields.Char(string="Attachment 3 Filename")

    @api.model
    def _get_manager_user_from_librarian(self, librarian_user_id):
        librarian_user = self.env['res.users'].browse(librarian_user_id)
        if not librarian_user:
            return False
        employee = self.env['hr.employee'].search(
            [('user_id', '=', librarian_user.id)],
            limit=1,
        )
        return employee.parent_id.user_id.id or False

    @api.model
    def _get_default_second_approver(self):
        user_id = int(
            self.env['ir.config_parameter'].sudo().get_param(
                'isy.default_second_approver_id',
                0,
            )
        )
        return user_id or False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'book.donation.request'
                ) or _('New')
            if not vals.get('first_approver_id'):
                librarian_id = vals.get('librarian_id') or self.env.user.id
                manager_user_id = self._get_manager_user_from_librarian(librarian_id)
                if manager_user_id:
                    vals['first_approver_id'] = manager_user_id
            if not vals.get('second_approver_id'):
                default_second = self._get_default_second_approver()
                if default_second:
                    vals['second_approver_id'] = default_second
        return super().create(vals_list)

    def _check_approvers_set(self):
        self.ensure_one()
        if not self.first_approver_id or not self.second_approver_id:
            raise UserError(
                _('Please set both first and second approvers before submitting.')
            )
        if self.first_approver_id == self.second_approver_id:
            raise UserError(
                _('First and second approvers must be different users.')
            )

    def _ensure_approver(self, approver):
        self.ensure_one()
        if self.env.user != approver:
            raise UserError(_('You are not allowed to perform this approval step.'))

    def action_submit(self):
        for request in self:
            if request.state != 'draft':
                raise UserError(_('Only draft requests can be submitted.'))
            request._check_approvers_set()
            request.state = 'first_approval'
            request.message_post(
                body=_('Submitted for first approval by %s.') % request.env.user.name,
                subtype_xmlid='mail.mt_note',
            )

    def action_first_approve(self):
        for request in self:
            if request.state != 'first_approval':
                raise UserError(_('This request is not waiting for first approval.'))
            request._ensure_approver(request.first_approver_id)
            request.write({
                'state': 'second_approval',
                'first_approval_date': fields.Datetime.now(),
            })
            request.message_post(
                body=_('Approved at first level by %s.') % request.env.user.name,
                subtype_xmlid='mail.mt_note',
            )

    def action_second_approve(self):
        for request in self:
            if request.state != 'second_approval':
                raise UserError(_('This request is not waiting for second approval.'))
            request._ensure_approver(request.second_approver_id)
            request.write({
                'state': 'approved',
                'second_approval_date': fields.Datetime.now(),
            })
            request.message_post(
                body=_('Approved at second level by %s.') % request.env.user.name,
                subtype_xmlid='mail.mt_note',
            )

    def action_reject(self):
        for request in self:
            if request.state not in ('first_approval', 'second_approval'):
                raise UserError(_('Only requests in approval can be rejected.'))
            if request.state == 'first_approval':
                request._ensure_approver(request.first_approver_id)
            else:
                request._ensure_approver(request.second_approver_id)
            if not request.rejection_reason:
                raise UserError(_('Please enter a rejection reason.'))
            request.state = 'rejected'
            request.message_post(
                body=_('Rejected by %s: %s')
                % (request.env.user.name, request.rejection_reason),
                subtype_xmlid='mail.mt_note',
            )

    def action_cancel(self):
        for request in self:
            if request.state != 'draft':
                raise UserError(_('Only draft requests can be cancelled.'))
            if request.librarian_id != request.env.user and not request.env.user.has_group(
                'book_donation_request.group_book_donation_manager'
            ):
                raise UserError(_('Only the librarian or a manager can cancel this request.'))
            request.state = 'cancelled'

    def action_reset_to_draft(self):
        for request in self:
            if request.state not in ('rejected', 'cancelled'):
                raise UserError(
                    _('Only rejected or cancelled requests can be reset to draft.')
                )
            if not request.env.user.has_group(
                'book_donation_request.group_book_donation_manager'
            ):
                raise UserError(_('Only managers can reset a request to draft.'))
            request.write({
                'state': 'draft',
                'first_approval_date': False,
                'second_approval_date': False,
                'rejection_reason': False,
            })
