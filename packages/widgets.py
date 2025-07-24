from django import forms

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True
    
    def __init__(self, attrs=None):
        attrs = attrs or {}
        attrs['multiple'] = True
        super().__init__(attrs)

    def value_from_datadict(self, data, files, name):
        if hasattr(files, 'getlist'):
            return files.getlist(name)
        return None

class MultipleFileField(forms.FileField):
    widget = MultipleFileInput
    
    def clean(self, data, initial=None):
        if data is None:
            return super().clean(data, initial)
            
        if not isinstance(data, (list, tuple)):
            data = [data]
            
        result = []
        for item in data:
            result.append(super().clean(item, initial))
        return result