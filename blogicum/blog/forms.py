from .models import Comments, Post
from django import forms
from django.contrib.auth.models import User


class PostForm(forms.ModelForm):    

    class Meta:
        # Указываем модель, на основе которой должна строиться форма.
        model = Post
        exclude = ('author', )        
        widgets = {
            'pub_date': forms.DateInput(attrs={'type': 'date'})            
        }


class CommentsForm(forms.ModelForm):

    class Meta:
        model = Comments
        fields = ('text',)


class ProfileEditForm(forms.ModelForm):

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
