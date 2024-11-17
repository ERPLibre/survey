#!/usr/bin/env python3
# © 2024 TechnoLibre (http://www.technolibre.ca)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import logging
from datetime import datetime

from dateutil.relativedelta import relativedelta
from pytz import timezone

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class SurveyQuestion(models.Model):
    _inherit = "survey.question"

    validation_min_multiple_choice_option = fields.Integer(
        string="Minimum Number of Answers",
        default=-1,
        help="The option is affected by validation_max_multiple_choice_option, limit "
        "the selection value to be choose. -1 disable this option.",
    )

    validation_max_multiple_choice_option = fields.Integer(
        string="Maximum Number of Answers",
        default=-1,
        help="The option is affected by validation_min_multiple_choice_option, limit "
        "the selection value to be choose. -1 disable this option.",
    )

    validation_min_datetime_option = fields.Selection(
        string="Minimum datetime option",
        selection=[
            ("today", "Today"),
        ],
        help="The option is affected by validation_max_datetime_option",
    )

    validation_max_datetime_option = fields.Selection(
        string="Maximum datetime option",
        selection=[
            ("today", "Today"),
        ],
        help="The option is affected by validation_min_datetime_option",
    )

    validation_min_date_option = fields.Selection(
        string="Minimum date option",
        selection=[
            ("today", "Today"),
        ],
        help="The option is affected by validation_max_date_option",
    )

    validation_max_date_option = fields.Selection(
        string="Maximum date option",
        selection=[
            ("today", "Today"),
        ],
        help="The option is affected by validation_min_date_option",
    )

    @api.depends("question_type")
    def _compute_validation_required(self):
        for question in self:
            if not question.validation_required or question.question_type not in [
                "char_box",
                "numerical_box",
                "date",
                "datetime",
                "multiple_choice",
            ]:
                question.validation_required = False

    def _validate_choice(self, answer, comment):
        res = super()._validate_choice(answer, comment)
        if (
            res
            or self.question_type != "multiple_choice"
            or not self.validation_required
        ):
            return res

        # When only 1 suggested answer is received from website in controller,
        # it should be given as a list of length 1: [sugg_ans_id],
        # but it is given as a string: str(sugg_ans_id)
        answer_count = len(answer) if isinstance(answer, list) else 1
        if self.validation_min_multiple_choice_option == -1:
            min_value = 0
        else:
            min_value = self.validation_min_multiple_choice_option
        if self.validation_max_multiple_choice_option == -1:
            max_value = len(self.suggested_answer_ids)
        else:
            max_value = self.validation_max_multiple_choice_option
        if not (min_value <= answer_count <= max_value):
            if min_value == max_value:
                return {
                    self.id: self.validation_error_msg
                    or _(
                        "You need to select %(min_value)s "
                        "answer, you chose %(len_answer)s answer.",
                        min_value=min_value,
                        len_answer=answer_count,
                    )
                }
            else:
                return {
                    self.id: self.validation_error_msg
                    or _(
                        "You need to select between %(min_value)s and %(max_value)s "
                        "answers, you chose %(len_answer)s answer.",
                        min_value=min_value,
                        max_value=max_value,
                        len_answer=answer_count,
                    )
                }
        return {}

    def _validate_date(self, answer):
        # Overwrite survey/models/survey_question.py
        is_datetime = self.question_type == "datetime"
        # Checks if user input is a date
        try:
            dateanswer = (
                fields.Datetime.from_string(answer)
                if is_datetime
                else fields.Date.from_string(answer)
            )
        except ValueError:
            return {self.id: _("This is not a date")}
        if not self.validation_required:
            return {}
        # Calculate delay time
        user_timezone = timezone(self.env.user.tz or "UTC")
        time_now = datetime.now(user_timezone)
        date_now = time_now.date()
        decalage_horaire = time_now.utcoffset().total_seconds() / 3600
        diff_hour = int(decalage_horaire)
        nb_second_delay = 0

        # Check if answer is in the right range
        if is_datetime:
            if self.validation_min_datetime_option:
                if self.validation_min_datetime_option == "today":
                    today = date_now
                    min_date = fields.datetime(
                        today.year, today.month, today.day
                    ) - relativedelta(hours=diff_hour)
                else:
                    _logger.error(
                        f"Missing information about validation_min_datetime_option: "
                        f"{self.validation_min_datetime_option}"
                    )
                    min_date = False
            else:
                min_date = fields.Datetime.from_string(self.validation_min_datetime)
            if self.validation_max_datetime_option:
                if self.validation_max_datetime_option == "today":
                    today = date_now + relativedelta(days=1)
                    nb_second_delay = 1
                    max_date = fields.datetime(
                        today.year,
                        today.month,
                        today.day,
                        -diff_hour,
                    ) - relativedelta(seconds=nb_second_delay)
                else:
                    _logger.error(
                        f"Missing information about validation_max_datetime_option: "
                        f"{self.validation_max_datetime_option}"
                    )
                    max_date = False
            else:
                max_date = fields.Datetime.from_string(self.validation_max_datetime)
        else:
            # date validation
            if self.validation_min_date_option:
                if self.validation_min_date_option == "today":
                    min_date = date_now
                else:
                    _logger.error(
                        f"Missing information about validation_min_date_option: "
                        f"{self.validation_min_date_option}"
                    )
                    min_date = False
            else:
                min_date = fields.Date.from_string(self.validation_min_date)
            if self.validation_max_date_option:
                if self.validation_max_date_option == "today":
                    max_date = date_now
                else:
                    _logger.error(
                        f"Missing information about validation_max_date_option: "
                        f"{self.validation_max_date_option}"
                    )
                    max_date = False
            else:
                max_date = fields.Date.from_string(self.validation_max_date)

        # Validation
        if min_date and max_date and not (min_date <= dateanswer <= max_date):
            date_min_show = (
                min_date - relativedelta(days=1)
                if not is_datetime
                else min_date.astimezone(user_timezone).strftime("%Y-%m-%d %H:%M:%S")
            )
            date_max_show = (
                max_date + relativedelta(days=1)
                if not is_datetime
                else (max_date + relativedelta(seconds=nb_second_delay))
                .astimezone(user_timezone)
                .strftime("%Y-%m-%d %H:%M:%S")
            )
            msg_error = self.validation_error_msg or _(
                "The date needs to be between %(date_min_show)s and %(date_max_show)s.",
                date_min_show=date_min_show,
                date_max_show=date_max_show,
            )
        elif min_date and not min_date <= dateanswer:
            date_min_show = (
                min_date - relativedelta(days=1)
                if not is_datetime
                else min_date.astimezone(user_timezone).strftime("%Y-%m-%d %H:%M:%S")
            )
            msg_error = self.validation_error_msg or _(
                "The date needs to be after %(date_min_show)s.",
                date_min_show=date_min_show,
            )
        elif max_date and not dateanswer <= max_date:
            date_max_show = (
                max_date + relativedelta(days=1)
                if not is_datetime
                else (max_date + relativedelta(seconds=1))
                .astimezone(user_timezone)
                .strftime("%Y-%m-%d %H:%M:%S")
            )
            msg_error = self.validation_error_msg or _(
                "The date needs to be before %(date_max_show)s.",
                date_max_show=date_max_show,
            )
        else:
            return {}

        return {self.id: msg_error}
