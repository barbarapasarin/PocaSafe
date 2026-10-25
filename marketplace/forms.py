from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Profile, CollectibleItem, Order, Review


class RegisterForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'class': 'input', 'placeholder': 'Nombre'}))
    last_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'class': 'input', 'placeholder': 'Apellido'}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'input', 'placeholder': 'correo@ejemplo.com'}))
    rut = forms.CharField(max_length=12, required=False, widget=forms.TextInput(attrs={'class': 'input', 'placeholder': '12.345.678-9'}))
    city = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'input', 'placeholder': 'Ciudad / Comuna'}))

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Nombre de usuario'}),
        }

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            Profile.objects.create(
                user=user,
                rut=self.cleaned_data.get('rut', ''),
                city=self.cleaned_data.get('city', '')
            )
        return user


class CollectibleItemForm(forms.ModelForm):
    class Meta:
        model = CollectibleItem
        fields = ['title', 'category', 'price', 'description', 'image']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Ej. Photocard Jungkook Golden Target'}),
            'category': forms.Select(attrs={'class': 'select'}),
            'price': forms.NumberInput(attrs={'class': 'input', 'placeholder': 'Precio en CLP'}),
            'description': forms.Textarea(attrs={'class': 'textarea', 'rows': 3, 'placeholder': 'Detalles del estado de la carta, embalaje, etc.'}),
            'image': forms.FileInput(attrs={'class': 'file-input'}),
        }


class OrderCreateForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['shipping_name', 'shipping_address']
        widgets = {
            'shipping_name': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Nombre completo del destinatario'}),
            'shipping_address': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Dirección de despacho (Comuna, Ciudad)'}),
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