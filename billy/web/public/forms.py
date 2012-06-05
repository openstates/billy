from django import forms
from django.conf import settings
#from django.contrib.admin.widgets import FilteredSelectMultiple

from billy.models import Metadata


def get_state_select_form(data):
    states = map(Metadata.get_object, sorted(settings.ACTIVE_STATES))
    state_abbrs = [('', 'Select a state')]
    state_abbrs += [(obj['_id'], obj['name']) for obj in states]

    class StateSelectForm(forms.Form):
        abbr = forms.ChoiceField(choices=state_abbrs, label="state")

    return StateSelectForm(data)


class ChamberSelectForm(forms.Form):

    chamber = forms.ChoiceField(widget=forms.RadioSelect())
    abbr = forms.CharField(widget=forms.HiddenInput())
    order = forms.IntegerField(widget=forms.HiddenInput(), initial=1)
    key = forms.CharField(widget=forms.HiddenInput(), initial='committee')

    @classmethod
    def unbound(cls, metadata, chamber='both', *args, **kwargs):

        inst = cls(*args, **kwargs)

        # Make the radio option names reflect this state's actual
        # chamber names.
        chamber_choices = [('upper', metadata['upper_chamber_name']),
                           ('lower', metadata['lower_chamber_name']),
                           ('both', 'All')]

        _chamber = inst.fields['chamber']
        _chamber.choices = chamber_choices
        _chamber.initial = chamber

        # Add in the state.
        inst.fields['abbr'].initial = metadata['_id']

        return inst


class FindYourLegislatorForm(forms.Form):
    address = forms.CharField()


def get_filter_bills_form(metadata):

    class FilterBillsForm(forms.Form):

        _bill_types = metadata.distinct_bill_types()
        _bill_subjects = metadata.distinct_bill_subjects()
        _action_types = metadata.distinct_action_types()
        _bill_sponsors = [leg.display_name() for leg in
                          metadata.legislators()]

        BILL_TYPES = zip(_bill_types, _bill_types)
        BILL_SUBJECTS = zip(_bill_subjects, _bill_subjects)
        ACTION_TYPES = zip(_action_types, _action_types)
        BILL_SPONSORS = zip(_bill_sponsors, _bill_sponsors)

        chambers = forms.MultipleChoiceField(
                    choices=(('upper', metadata['upper_chamber_name']),
                             ('lowerl', metadata['lower_chamber_name'])),
                    widget=forms.CheckboxSelectMultiple())

        bill_types = forms.MultipleChoiceField(
                        choices=BILL_TYPES,
                        widget=forms.CheckboxSelectMultiple())

        subjects = forms.MultipleChoiceField(
                    choices=BILL_SUBJECTS,
                    widget=forms.CheckboxSelectMultiple()
                    #widget=FilteredSelectMultiple("Subjects", is_stacked=False)
                    )

        actions = forms.MultipleChoiceField(
                    choices=ACTION_TYPES,
                    widget=forms.CheckboxSelectMultiple()
                    #widget=FilteredSelectMultiple("Actions", is_stacked=False)
                    )

        sponsors = forms.MultipleChoiceField(
                    choices=BILL_SPONSORS,
                    widget=forms.CheckboxSelectMultiple()
                    #widget=FilteredSelectMultiple("Sponsors", is_stacked=False)
                    )

    return FilterBillsForm
