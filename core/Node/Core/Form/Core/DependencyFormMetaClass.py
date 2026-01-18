from django.forms.fields import Field
from typing import Any, Dict, List
from django.forms.forms import DeclarativeFieldsMetaclass

from .exceptions import (
    MissingDependencyError,
    SelfReferenceError,
    MissingLoaderError,
    NonCallableLoaderError,
)




class DependencyFormMetaClass(DeclarativeFieldsMetaclass):
    """
    Metaclass for Django forms that enables field dependency management.
    
    This metaclass processes form fields that have dependencies and automatically
    sets up the dependency resolution system. It validates dependencies, resolves
    loader functions, and creates a `_field_dependencies` dictionary on the form class.
    
    **What it does:**
    1. Scans all form fields for those with a `dependent_on` attribute
    2. Validates that all dependencies reference existing form fields
    3. Prevents self-referential dependencies
    4. Resolves loader functions (either from field.loader or {field_name}_loader method)
    5. Creates a `_field_dependencies` dictionary mapping field names to their
       dependency metadata (dependent_on list and loader function)
    """
    
    def __new__(mcls, name, bases, attrs):
        
        # DeclarativeFieldsMetaclass __new__ method. Finds all class attributes that are instances of `Field` Removes them from the class namespace and adds them to the `base_fields` dictionary.
        cls = super().__new__(mcls, name, bases, attrs) 

        base_fields:Dict[str, Field] = cls.base_fields
        cls._field_dependencies:Dict[str, Dict[str, Any]] = {}
        field_names:List[str] = base_fields.keys()

        for field_name, field in base_fields.items():
            if hasattr(field, "dependent_on") and field.dependent_on:

                # Validate dependencies
                for dep in field.dependent_on:
                    if dep not in field_names:
                        raise MissingDependencyError(
                            f"{name}.{field_name} depends on '{dep}', "
                            f"but no such field exists."
                        )
                    if dep == field_name:
                        raise SelfReferenceError(
                            f"{name}.{field_name} cannot depend on itself."
                        )

                # Resolve loader
                loader = field.loader
                if loader is None:
                    loader_name = f"{field_name}_loader"
                    loader = attrs.get(loader_name)

                if loader is None:
                    raise MissingLoaderError(
                        f"{name}.{field_name} requires a loader. "
                        f"Define '{field_name}_loader' or pass loader=."
                    )

                if not callable(loader):
                    raise NonCallableLoaderError(
                        f"{name}.{field_name} requires a loader. "
                        f"The provided loader is not callable."
                    )

                cls._field_dependencies[field_name] = {
                    "dependent_on": field.dependent_on,
                    "loader": loader,
                }
        return cls
