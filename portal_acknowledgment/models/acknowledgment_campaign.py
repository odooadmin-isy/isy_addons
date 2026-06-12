# -*- coding: utf-8 -*-

import re

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PortalAcknowledgmentCampaign(models.Model):
    _name = 'portal.acknowledgment.campaign'
    _description = 'Portal Acknowledgment Campaign'
    _order = 'id desc'

    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)
    tab1_title = fields.Char(
        string='Tab 1 Title',
        default='Information',
        translate=True,
    )
    tab1_content = fields.Html(string='Tab 1 Content', translate=True, sanitize_attributes=False)
    tab1_extra_html = fields.Html(
        string='Tab 1 Extra HTML',
        translate=True,
        sanitize_attributes=False,
        help='Optional extra text or HTML block shown in the first tab.',
    )
    tab2_title = fields.Char(
        string='Tab 2 Title',
        default='Video',
        translate=True,
    )
    tab2_youtube_url = fields.Char(
        string='YouTube URL',
        help='Full YouTube link (watch, youtu.be, or embed URL).',
    )
    tab3_title = fields.Char(
        string='Tab 3 Title',
        default='Additional Information',
        translate=True,
    )
    tab3_content = fields.Html(string='Tab 3 Content', translate=True, sanitize_attributes=False)
    tab3_extra_html = fields.Html(
        string='Tab 3 Extra HTML',
        translate=True,
        sanitize_attributes=False,
        help='Optional extra text or HTML block shown in the last tab.',
    )
    communication_coordinator_ids = fields.Many2many(
        'hr.employee',
        'portal_ack_campaign_hr_employee_rel',
        'campaign_id',
        'employee_id',
        string='Communication Coordinators',
        help='These coordinators are CC-ed when an employee submits this acknowledgment.',
    )
    submission_ids = fields.One2many(
        'portal.acknowledgment.submission',
        'campaign_id',
        string='Submissions',
    )
    submission_count = fields.Integer(compute='_compute_submission_count')

    @api.depends('submission_ids')
    def _compute_submission_count(self):
        for campaign in self:
            campaign.submission_count = len(campaign.submission_ids)

    def action_view_submissions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Submissions'),
            'res_model': 'portal.acknowledgment.submission',
            'view_mode': 'tree,form',
            'domain': [('campaign_id', '=', self.id)],
            'context': {'default_campaign_id': self.id},
        }

    @api.constrains('active')
    def _check_single_active_campaign(self):
        for campaign in self.filtered('active'):
            other_active = self.search([
                ('active', '=', True),
                ('id', '!=', campaign.id),
            ])
            if other_active:
                raise ValidationError(
                    _('Only one acknowledgment campaign can be active at a time. '
                      'Deactivate "%s" first.') % other_active[0].name
                )

    def get_youtube_video_id(self):
        """Extract YouTube video ID from the configured URL."""
        self.ensure_one()
        url = (self.tab2_youtube_url or '').strip()
        if not url:
            return False
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com/shorts/([a-zA-Z0-9_-]{11})',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return False
