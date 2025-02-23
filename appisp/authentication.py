from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from appisp.models import EmpresaToken


class EmpresaTokenAuthentication(BaseAuthentication):
    def authenticate(self, request):
        token = request.headers.get("Authorization")
        if not token:
            return None

        token = token.replace("Token ", "")  # Remove o prefixo "Token "

        try:
            empresa_token = EmpresaToken.objects.get(token=token)
            return (empresa_token.empresa, None)
        except EmpresaToken.DoesNotExist:
            raise AuthenticationFailed("Token inválido")
