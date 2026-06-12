# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.exceptions import UserError


class PortalAcknowledgment(CustomerPortal):

    def _get_active_campaign(self):
        return request.env['portal.acknowledgment.campaign'].sudo().search([
            ('active', '=', True),
        ], limit=1)

    def _get_user_submission(self, campaign, user):
        if not campaign:
            return request.env['portal.acknowledgment.submission']
        
        return request.env['portal.acknowledgment.submission'].sudo().search([
            ('campaign_id', '=', campaign.id),
            ('user_id', '=', user.id),
        ], limit=1)

    def _prepare_acknowledgment_values(self):
        user = request.env.user
        campaign = self._get_active_campaign()
        submission = self._get_user_submission(campaign, user)
        employee = request.env['portal.acknowledgment.submission']._get_employee_for_user(user)
        youtube_id = campaign.get_youtube_video_id() if campaign else False
        error_message = request.session.pop('acknowledgment_error', False)
        is_eligible = bool(employee and employee.is_new_employee_for_acknowledgment())
        return {
            'campaign': campaign,
            'submission': submission,
            'already_submitted': bool(submission),
            'is_acknowledgment_eligible': is_eligible,
            'youtube_video_id': youtube_id,
            'page_name': 'acknowledgment',
            'error_message': error_message,
        }

    def _is_user_eligible_for_acknowledgment(self, user):
        employee = request.env['portal.acknowledgment.submission']._get_employee_for_user(user)
        print("employee", employee.name)
        return bool(employee and employee.is_new_employee_for_acknowledgment())

    def _prepare_portal_layout_values(self):
        values = super()._prepare_portal_layout_values()
        values['show_acknowledgment_portal'] = self._show_acknowledgment_portal()
        return values

    def _show_acknowledgment_portal(self):
        user = request.env.user
        campaign = self._get_active_campaign()
        if not campaign:
            return False
        if not self._is_user_eligible_for_acknowledgment(user):
            print("User is not eligible for acknowledgment")
            return False
        submission = self._get_user_submission(campaign, user)
        print("submission", submission)
        return not bool(submission)

    @http.route(['/my/acknowledgment'], type='http', auth='user', website=True)
    def portal_acknowledgment(self, **kw):
        values = self._prepare_portal_layout_values()
        values.update(self._prepare_acknowledgment_values())
        return request.render('portal_acknowledgment.portal_acknowledgment_form', values)

    @http.route(['/my/acknowledgment/submit'], type='http', auth='user', website=True, methods=['POST'])
    def portal_acknowledgment_submit(self, **post):
        campaign = self._get_active_campaign()
        if not campaign:
            return request.redirect('/my/acknowledgment?error=no_campaign')

        tab1 = post.get('tab1_acknowledged') == 'on'
        tab2 = post.get('tab2_acknowledged') == 'on'
        tab3 = post.get('tab3_acknowledged') == 'on'

        Submission = request.env['portal.acknowledgment.submission']
        try:
            Submission.submit_from_portal(
                campaign,
                request.env.user,
                tab1,
                tab2,
                tab3,
            )
        except UserError as err:
            request.session['acknowledgment_error'] = str(err.args[0])
            return request.redirect('/my/acknowledgment?error=validation')

        return request.redirect('/my/acknowledgment?submitted=1')
