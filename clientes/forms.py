from django import forms
from django.contrib.auth.models import User
import re

class ClienteImportForm(forms.Form):
    clientes = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label="Selecione os clientes para importar"
    )


class ClienteSenhaForm(forms.ModelForm):
    nova_senha = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label="Nova Senha",
        required=True,
        
    )
    confirmar_senha = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label="Confirmar Nova Senha",
        required=True,
    )

    class Meta:
        model = User
        fields = []

    def clean_nova_senha(self):
        senha = self.cleaned_data.get("nova_senha")

        # Comprimento mínimo
        if len(senha) < 8:
            raise forms.ValidationError("A senha deve ter pelo menos 8 caracteres.")

        # Pelo menos uma letra maiúscula
        if not any(char.isupper() for char in senha):
            raise forms.ValidationError("A senha deve conter pelo menos uma letra maiúscula.")

        # Pelo menos uma letra minúscula
        if not any(char.islower() for char in senha):
            raise forms.ValidationError("A senha deve conter pelo menos uma letra minúscula.")

        # Pelo menos um número
        if not any(char.isdigit() for char in senha):
            raise forms.ValidationError("A senha deve conter pelo menos um número.")

        # Pelo menos um caractere especial
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", senha):
            raise forms.ValidationError("A senha deve conter pelo menos um caractere especial (!@#$%^&*(),.?\":{}|<>).")

        return senha

    def clean(self):
        cleaned_data = super().clean()
        nova_senha = cleaned_data.get("nova_senha")
        confirmar_senha = cleaned_data.get("confirmar_senha")

        if nova_senha != confirmar_senha:
            raise forms.ValidationError("As senhas não coincidem.")
        return cleaned_data