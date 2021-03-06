# -*- coding: utf-8 -*-
# Copyright 2016 Odoo S. A.
# Copyright 2017 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models
from dateutil import rrule


class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    def _get_weekdays(self):
        """ Return the list of weekdays that contain at least one working
        interval. There's a special context key for returning all.
        """
        self.ensure_one()
        return list({int(d) for d in self.attendance_ids.mapped('dayofweek')})

    def _iter_work_intervals(self, start_dt, end_dt, leaves=None):
        """ Lists the current resource's work intervals between the two
        provided datetimes (inclusive) expressed in UTC, for each worked day.
        """
        real_weekdays = self._get_weekdays()
        if self.env.context.get('include_rest_days'):
            full_weekdays = range(7)
        else:
            full_weekdays = real_weekdays
        for day in rrule.rrule(rrule.DAILY, dtstart=start_dt.date(),
                               until=end_dt.date(), byweekday=full_weekdays):
            # get_working_intervals_of_day can only accept interval of one day
            # the following intends to split it in two intervals
            start_date = (
                start_dt if day.date() == start_dt.date() else day.replace(
                    hour=0, minute=0, second=0, microsecond=0,
                )
            )
            end_date = (
                end_dt if day.date() == end_dt.date() else day.replace(
                    hour=23, minute=59, second=59, microsecond=999999,
                )
            )
            if day.weekday() in real_weekdays:
                intervals = self.get_working_intervals_of_day(
                    start_dt=start_date, end_dt=end_date,
                    leaves=leaves, compute_leaves=False,
                )
            else:  # Include full day for rest days - Will be handled later
                intervals = [(start_date, end_date)]
            if intervals:
                yield intervals
