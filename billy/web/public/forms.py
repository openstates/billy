from django import forms

from billy import db


states = db.metadata.find({}, {'_id': 1, 'name': 1}, sort=[('name', 1)])
state_abbrs = [('', 'Select a state')]
state_abbrs += [(obj['_id'], obj['name']) for obj in states]


class StateSelectForm(forms.Form):
    abbr = forms.ChoiceField(choices=state_abbrs, label="state")


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
