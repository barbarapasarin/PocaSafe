from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Profile, CollectibleItem, Order, Review, CHILE_REGIONS

REGION_SELECT_CHOICES = [('', 'Selecciona una región')] + list(CHILE_REGIONS)


class RegisterForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=30,
        required=True,
        label='Nombre',
        widget=forms.TextInput(attrs={'class': 'input', 'placeholder': 'Nombre'})
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        label='Apellido',
        widget=forms.TextInput(attrs={'class': 'input', 'placeholder': 'Apellido'})
    )
    email = forms.EmailField(
        required=True,
        label='Correo electrónico',
        widget=forms.EmailInput(attrs={'class': 'input', 'placeholder': 'correo@ejemplo.com'})
    )
    rut = forms.CharField(
        max_length=12,
        required=False,
        label='RUT',
        widget=forms.TextInput(attrs={'class': 'input', 'placeholder': '12.345.678-9'})
    )
    phone = forms.CharField(
        max_length=15,
        required=False,
        label='Teléfono de contacto',
        widget=forms.TextInput(attrs={'class': 'input', 'placeholder': '+56 9 1234 5678'})
    )
    address = forms.CharField(
        max_length=255,
        required=False,
        label='Dirección o Sucursal Courier',
        widget=forms.TextInput(attrs={'class': 'input', 'placeholder': 'Dirección o sucursal Starken/Chilexpress'})
    )
    city = forms.CharField(
        max_length=100,
        required=False,
        label='Comuna / Ciudad',
        widget=forms.TextInput(attrs={'class': 'input', 'placeholder': 'Ej. San Bernardo'})
    )
    region = forms.ChoiceField(
        choices=REGION_SELECT_CHOICES,
        required=False,
        label='Región',
        widget=forms.Select(attrs={'class': 'input'})
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')
        labels = {
            'username': 'Nombre de usuario',
        }
        widgets = {
            'username': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Nombre de usuario'}),
        }

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            Profile.objects.create(
                user=user,
                rut=self.cleaned_data.get('rut', ''),
                phone=self.cleaned_data.get('phone', ''),
                address=self.cleaned_data.get('address', ''),
                city=self.cleaned_data.get('city', ''),
                region=self.cleaned_data.get('region', ''),
            )
        return user


class CollectibleItemForm(forms.ModelForm):
    class Meta:
        model = CollectibleItem
        fields = ['title', 'category', 'tags', 'price', 'description', 'image']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Ej. Photocard RM Indigo'}),
            'category': forms.Select(attrs={'class': 'select'}),
            'tags': forms.TextInput(attrs={
                'class': 'input',
                'placeholder': 'Ej: BTS, RM, Album PC, Indigo (separados por coma)'
            }),
            'price': forms.NumberInput(attrs={'class': 'input', 'placeholder': 'Precio en CLP'}),
            'description': forms.Textarea(attrs={'class': 'textarea', 'rows': 3, 'placeholder': 'Detalles del estado de la carta, embalaje, toploader, etc.'}),
            'image': forms.FileInput(attrs={'class': 'file-input'}),
        }


class OrderCreateForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['shipping_name', 'shipping_rut', 'shipping_phone', 'shipping_address', 'shipping_city', 'shipping_region']
        widgets = {
            'shipping_name': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Nombre completo de quien recibe'}),
            'shipping_rut': forms.TextInput(attrs={'class': 'input', 'placeholder': 'RUT (ej. 12.345.678-9) exigido por courier'}),
            'shipping_phone': forms.TextInput(attrs={'class': 'input', 'placeholder': '+56 9 1234 5678'}),
            'shipping_address': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Domicilio o Sucursal Starken / Correos / Chilexpress'}),
            'shipping_city': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Comuna / Ciudad (ej. San Bernardo)'}),
            'shipping_region': forms.Select(attrs={'class': 'input'}),
        }


class ReviewForm(forms.ModelForm):
    RATING_CHOICES = [
        (5, '⭐⭐⭐⭐⭐ (Excelente)'),
        (4, '⭐⭐⭐⭐ (Muy Bueno)'),
        (3, '⭐⭐⭐ (Aceptable)'),
        (2, '⭐⭐ (Regular)'),
        (1, '⭐ (Deficiente)'),
    ]
    rating = forms.ChoiceField(
        choices=RATING_CHOICES,
        widget=forms.Select(attrs={'class': 'select'}),
        label="Calificación"
    )
    comment = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'textarea',
            'rows': 3,
            'placeholder': 'Describe cómo llegó el embalaje, el estado del coleccionable o la rapidez del envío...'
        }),
        required=False,
        label="Comentario de Experiencia"
    )

    class Meta:
        model = Review
        fields = ['rating', 'comment']


class ProfileUpdateForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={'class': 'input is-small', 'placeholder': 'Nombre'})
    )
    last_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={'class': 'input is-small', 'placeholder': 'Apellido'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'input is-small', 'placeholder': 'correo@ejemplo.com'})
    )

    class Meta:
        model = Profile
        fields = ['rut', 'phone', 'address', 'city', 'region']
        widgets = {
            'rut': forms.TextInput(attrs={'class': 'input is-small', 'placeholder': '12.345.678-9'}),
            'phone': forms.TextInput(attrs={'class': 'input is-small', 'placeholder': '+56 9 1234 5678'}),
            'address': forms.TextInput(attrs={'class': 'input is-small', 'placeholder': 'Dirección o Sucursal Starken/Chilexpress'}),
            'city': forms.TextInput(attrs={'class': 'input is-small', 'placeholder': 'Comuna / Ciudad'}),
            'region': forms.Select(attrs={'class': 'input is-small'}),
        }