from django import forms


class DependentChoiceField(forms.ChoiceField):
    """
    A ChoiceField that depends on other fields for its choices.
    
    The `dependent_on` and `loader` attributes are immutable after initialization.
    """
    
    def __init__(self, *args, dependent_on=None, loader=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Store as tuple for immutability
        self._dependent_on = tuple(dependent_on) if dependent_on else ()
        self._loader = loader

    @property
    def dependent_on(self):
        """Read-only list of field names this field depends on."""
        return list(self._dependent_on)

    @dependent_on.setter
    def dependent_on(self, value):
        raise AttributeError("'dependent_on' is read-only after initialization")

    @property
    def loader(self):
        """Read-only loader function for this field."""
        return self._loader

    @loader.setter
    def loader(self, value):
        raise AttributeError("'loader' is read-only after initialization")
