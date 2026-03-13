from django import forms

from .models import FvMetadata


class BaseFvMetadataForm(forms.ModelForm):
    fixed_categoria_fv = None
    fixed_is_ppu = None
    fixed_is_in_costruzione = None

    class Meta:
        model = FvMetadata
        fields = (
            "nome_impianto",
            "nome_proprietario",
            "nome_cliente",
            "data_inizio_contratto",
            "data_fine_contratto",
            "pr_contrattuale",
            "potenza",
            "note",
            "impianto",
        )
        widgets = {
            "data_inizio_contratto": forms.DateInput(attrs={"type": "date"}),
            "data_fine_contratto": forms.DateInput(attrs={"type": "date"}),
            "note": forms.Textarea(attrs={"rows": 4}),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.fixed_categoria_fv is not None:
            instance.categoria_fv = self.fixed_categoria_fv
        if self.fixed_is_ppu is not None:
            instance.is_ppu = self.fixed_is_ppu
        if self.fixed_is_in_costruzione is not None:
            instance.is_in_costruzione = self.fixed_is_in_costruzione
        if commit:
            instance.save()
        return instance


class FvClientiForm(BaseFvMetadataForm):
    fixed_categoria_fv = FvMetadata.CategoriaFv.CLIENTE
    fixed_is_ppu = False
    fixed_is_in_costruzione = False


class FvProprietaForm(BaseFvMetadataForm):
    fixed_categoria_fv = FvMetadata.CategoriaFv.PROPRIETA
    fixed_is_ppu = False
    fixed_is_in_costruzione = False


class FvInCostruzioneForm(BaseFvMetadataForm):
    fixed_categoria_fv = FvMetadata.CategoriaFv.CLIENTE
    fixed_is_ppu = False
    fixed_is_in_costruzione = True


class FvPpuForm(BaseFvMetadataForm):
    fixed_categoria_fv = FvMetadata.CategoriaFv.CLIENTE
    fixed_is_ppu = True
    fixed_is_in_costruzione = False
