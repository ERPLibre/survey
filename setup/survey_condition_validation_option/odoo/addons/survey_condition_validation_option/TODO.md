About datetime or date, when enable condition, the limitation can be set into widget and
not only on server side. Check python controller method `survey_print` to edit xml_id
view `question_date` and `survey.survey_page_print`. Need to overwrite

```
t-att-data-mindate="question.validation_min_date"
t-att-data-maxdate="question.validation_max_date"
```
