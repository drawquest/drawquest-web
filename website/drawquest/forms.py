from django import forms


class SupportForm(forms.Form):
    username = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'id': 'support_page_username'}))
    message = forms.CharField(widget=forms.Textarea(attrs={'rows': 5}))
    sender = forms.EmailField(widget=forms.TextInput(attrs={'id': 'support_page_email', 'type': 'email'}))

