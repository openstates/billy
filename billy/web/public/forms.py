from django import forms

from billy.models import db

_all_abbrs = [('', '')]
_all_metadata = db.metadata.find({}, fields=('name',)).sort('name')
_all_abbrs += [(m['_id'], m['name']) for m in _all_metadata]


def get_region_select_form(data):

    class RegionSelectForm(forms.Form):
        abbr = forms.ChoiceField(choices=_all_abbrs, label="abbr")

    return RegionSelectForm(data)


def get_filter_bills_form(metadata):

    class FilterBillsForm(forms.Form):

        search_text = forms.CharField(required=False)

        # `metadata` will be None if the search is across all bills
        if metadata:
            _bill_types = metadata.distinct_bill_types()
            _bill_subjects = metadata.distinct_bill_subjects()
            _bill_sponsors = [(leg['_id'], leg.display_name()) for leg in
                              metadata.legislators()]
            _sessions = [(s['id'], s['name']) for s in metadata.sessions()]

            BILL_TYPES = [('', '')] + zip(_bill_types, [s.title()
                                                        for s in _bill_types])
            BILL_SUBJECTS = zip(_bill_subjects, _bill_subjects)
            BILL_SPONSORS = [('', '')] + _bill_sponsors
            SESSIONS = [('', '')] + _sessions

            session = forms.ChoiceField(choices=SESSIONS, required=False)

            _status_choices = []
            _chamber_choices = [('', 'Both Chambers')]
            for chamber_type in metadata['chambers']:
                chamber_name = metadata['chambers'][chamber_type]['name']
                _status_choices.append(('passed_' + chamber_type,
                                        'Passed ' + chamber_name))
                _chamber_choices.append((chamber_type, chamber_name))
            _status_choices.append(('signed', 'Signed'))

            if len(_chamber_choices) > 2:
                chamber = forms.MultipleChoiceField(
                    choices=_chamber_choices,
                    widget=forms.RadioSelect(),
                    required=False)

            status = forms.MultipleChoiceField(
                choices=_status_choices,
                widget=forms.CheckboxSelectMultiple(),
                required=False)

            sponsor__leg_id = forms.ChoiceField(choices=BILL_SPONSORS,
                                                required=False,
                                                label='Sponsor name')

            type = forms.ChoiceField(choices=BILL_TYPES, required=False)

            subjects = forms.MultipleChoiceField(choices=BILL_SUBJECTS,
                                                 required=False)
        else:
            abbr = forms.ChoiceField(choices=_all_abbrs, label="abbr")
            chamber = forms.MultipleChoiceField(
                choices=(('upper', 'upper'), ('lower', 'lower')),
                widget=forms.CheckboxSelectMultiple(), required=False)

            status = forms.MultipleChoiceField(
                choices=(
                    ('passed_lower', 'Passed lower'),
                    ('passed_upper', 'Passed upper'),
                    ('signed', 'Signed'),
                ),
                widget=forms.CheckboxSelectMultiple(),
                required=False)

    return FilterBillsForm
