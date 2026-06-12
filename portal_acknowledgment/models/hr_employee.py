# -*- coding: utf-8 -*-

from datetime import date, datetime

from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    @api.model
    def _get_acknowledgment_period_cutoff(self, reference_date=None):
        """Return the July 1 cutoff for the current acknowledgment period.

        Examples (today -> cutoff):
        - Aug 2026 .. Dec 2026 -> 2026-07-01
        - Jan 2027 .. Jun 2027 -> 2026-07-01
        - Jul 2026 -> 2026-07-01
        - Jan 2026 .. Jun 2026 -> 2025-07-01
        """
        today = reference_date or fields.Date.context_today(self)
        if isinstance(today, str):
            today = fields.Date.to_date(today)
        if today.month > 7:
            period_start_year = today.year
        elif today.month < 7:
            period_start_year = today.year - 1
        else:
            period_start_year = today.year
        return date(period_start_year, 7, 1)

    def _get_acknowledgment_join_date(self):
        self.ensure_one()
        join_date = False
        for field_name in ('x_studio_joining_date', 'x_hire_date', 'first_contract_date'):
            if field_name in self._fields and self[field_name]:
                join_date = self[field_name]
                break
        if not join_date:
            return False
        if isinstance(join_date, datetime):
            return join_date.date()
        return fields.Date.to_date(join_date)

    def is_new_employee_for_acknowledgment(self, reference_date=None):
        """Employee is new when join date is after the dynamic July 1 cutoff."""
        self.ensure_one()
        join_date = self._get_acknowledgment_join_date()
        if not join_date:
            return False
        cutoff = self._get_acknowledgment_period_cutoff(reference_date)
        return join_date > cutoff
