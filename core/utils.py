from django.core.exceptions import ImproperlyConfigured

def get_empresa_from_user(user):
    if not hasattr(user, 'perfil'):
        raise ImproperlyConfigured('Usuário sem perfil configurado.')
    return user.perfil.empresa
