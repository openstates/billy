from django import forms
from django.conf import settings

from billy.models import Metadata


def get_state_select_form():
    states = map(Metadata.get_object, sorted(settings.ACTIVE_STATES))
    state_abbrs = [('', 'Select a state')]
    state_abbrs += [(obj['_id'], obj['name']) for obj in states]

    class StateSelectForm(forms.Form):
        abbr = forms.ChoiceField(choices=state_abbrs, label="state")

    return StateSelectForm


class ChamberSelectForm(forms.Form):

    chamber = forms.ChoiceField(widget=forms.RadioSelect())
    abbr = forms.CharField(widget=forms.HiddenInput())

    @classmethod
    def unbound(cls, metadata, chamber='both'):

        inst = cls()

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
