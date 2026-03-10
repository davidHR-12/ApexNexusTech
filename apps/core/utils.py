from django import forms


class TailwindModelForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        BASE    = "w-full bg-[#0f172a] border border-gray-700 rounded-xl px-4 py-3 text-white outline-none focus:border-[#10b981] transition-all"
        FILE    = (
            "w-full bg-[#0f172a] border border-gray-700 rounded-xl py-2 px-4 text-gray-400 "
            "focus:border-[#10b981] outline-none transition text-sm "
            "file:mr-4 file:py-1.5 file:px-4 file:rounded-lg file:border-0 "
            "file:text-sm file:font-bold file:bg-[#10b981]/10 file:text-[#10b981] "
            "hover:file:bg-[#10b981]/20"
        )
        CHECK   = "rounded border-gray-700 text-[#10b981] focus:ring-[#10b981] bg-gray-900"

        for field in self.fields.values():
            w = field.widget
            if isinstance(w, (forms.ClearableFileInput, forms.FileInput)):
                w.attrs["class"] = FILE
            elif isinstance(w, forms.CheckboxInput):
                w.attrs["class"] = CHECK
            elif isinstance(w, forms.Textarea):
                w.attrs["class"] = f"{BASE} font-mono text-sm"
            elif isinstance(w, forms.Select):
                w.attrs["class"] = f"{BASE} appearance-none"
            else:
                # TextInput, NumberInput, EmailInput, URLInput, HiddenInput, etc.
                w.attrs.setdefault("class", BASE)