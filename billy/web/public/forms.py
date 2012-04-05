from django import forms

from billy import db


state_abbrs = [(obj['_id'], obj['name']) for obj in
               db.metadata.find({}, {'_id': 1, 'name': 1})]

class StateSelectForm(forms.Form):
    abbr = forms.ChoiceField(choices=state_abbrs, label="state")
