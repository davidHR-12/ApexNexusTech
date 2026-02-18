from django import forms


class TailwindModelForm(forms.ModelForm):
    widgets = {
        "gramos_por_unidad": forms.NumberInput(
            attrs={"placeholder": "Ej: 100", "step": "0.1"}
        ),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            # Clases base
            base_classes = "w-full bg-[#0f172a] border border-gray-700 rounded-xl px-4 py-3 text-white outline-none focus:border-[#10b981] transition-all"

            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = (
                    "rounded border-gray-700 text-[#10b981] focus:ring-[#10b981] bg-gray-900"
                )
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs["class"] = f"{base_classes} font-mono text-sm"
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs["class"] = f"{base_classes} appearance-none"
            else:
                field.widget.attrs["class"] = base_classes
