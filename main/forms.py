from django import forms
from django.contrib.auth.models import User
from models import Account

class UserCreationFormWithEmail(forms.ModelForm):
	'''UserCreationForm with email as username rather than a seperate username'''
	"""
    A form that creates a user, with no privileges, from the given email and
    password.
    """
	error_messages = {
		'password_mismatch': ("The two password fields didn't match."),
	}
	first_name = forms.CharField(label='First Name', max_length=30)
	last_name = forms.CharField(label='Last Name', max_length=30)
	username = forms.EmailField(label=('Email'), max_length=64, help_text='Input email here')
	password1 = forms.CharField(label= ('Password'),
		widget=forms.PasswordInput)
	password2 = forms.CharField(label= ('Retype Password'),
		widget=forms.PasswordInput,
		help_text= ('Enter the same password as above, for verification.'))
	car_id = forms.CharField(label= ('car_id_test'), help_text= ('This should not be in production build'))
	phone = forms.CharField(label=('Phone Number'), max_length=20, required=False,help_text='Optional')

	class Meta:
		model = User
		fields = ('first_name','last_name','username', 'password1', 'password2','car_id','phone')

	def clean_email(self):
		email = self.cleaned_data['username']
		return email

	def clean_password2(self):
		password1 = self.cleaned_data.get('password1')
		password2 = self.cleaned_data.get('password2')
		if password1 and password2 and password1 != password2:
			raise forms.ValidationError(
				self.error_messages['password_mismatch'],
				code='password_mismatch',
			)
		return password2

	def save(self, commit=True):
		user = super(UserCreationFormWithEmail, self).save(commit=False)
		user.set_password(self.cleaned_data['password1'])
		if commit:
			user.save()
		return user

class SimpleUserCreationFormWithEmail(forms.ModelForm):
	'''UserCreationForm with email as username rather than a seperate username'''
	"""
    A form that creates a user, with no privileges, from the given email and
    password.
    """
	error_messages = {
		'password_mismatch': ("The two password fields didn't match."),
	}
	first_name = forms.CharField(label='First Name', max_length=30,widget=forms.TextInput(attrs={'class':'form-control'}))
	last_name = forms.CharField(label='Last Name', max_length=30,widget=forms.TextInput(attrs={'class':'form-control'}))
	username = forms.EmailField(label=('Email'), max_length=64, widget=forms.TextInput(attrs={'class':'form-control'}))
	password1 = forms.CharField(label= ('Password'),		widget=forms.PasswordInput(attrs={'class':'form-control'}))
	password2 = forms.CharField(label= ('Retype Password'),		widget=forms.PasswordInput(attrs={'class':'form-control'}),
		help_text= ('Enter the same password as above, for verification.'))


	class Meta:
		model = User
		fields = ('first_name','last_name','username', 'password1', 'password2')

	def clean_email(self):
		email = self.cleaned_data['username']
		return email

	def clean_password2(self):
		password1 = self.cleaned_data.get('password1')
		password2 = self.cleaned_data.get('password2')
		if password1 and password2 and password1 != password2:
			raise forms.ValidationError(
				self.error_messages['password_mismatch'],
				code='password_mismatch',
			)
		return password2

	def save(self, commit=True):
		user = super(SimpleUserCreationFormWithEmail, self).save(commit=False)
		user.set_password(self.cleaned_data['password1'])
		if commit:
			user.save()
		return user

class SimpleUserLoginFormWithEmail(forms.ModelForm):
	'''UserCreationForm with email as username rather than a seperate username'''
	"""
    A form that creates a user, with no privileges, from the given email and
    password.
    """
	error_messages = {
		'password_mismatch': ("The two password fields didn't match."),
	}
	username = forms.EmailField(label=('Email'), max_length=64, widget=forms.TextInput(attrs={'class':'form-control'}))
	password1 = forms.CharField(label= ('Password'),widget=forms.PasswordInput(attrs={'class':'form-control'}))

	class Meta:
		model = User
		fields = ('username', 'password1')

	def clean_email(self):
		email = self.cleaned_data['username']
		return email

	def save(self, commit=True):
		user = super(SimpleUserLoginFormWithEmail, self).save(commit=False)
		user.set_password(self.cleaned_data['password1'])
		if commit:
			user.save()
		return user