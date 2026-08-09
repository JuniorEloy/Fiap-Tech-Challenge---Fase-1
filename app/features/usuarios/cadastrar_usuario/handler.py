from fastapi import HTTPException, status
from app.features.usuarios.models import Usuario
from app.features.usuarios.repository import UsuarioRepository
from app.features.usuarios.cadastrar_usuario.schemas import (
    CriarUsuarioRequest,
    UsuarioResponse,
)
from app.shared.security.password import gerar_hash_senha
from app.shared.domain.value_objects.email import Email


class CadastrarUsuarioHandler:
    def __init__(self, repository: UsuarioRepository):
        self.repository = repository

    async def executar(self, command: CriarUsuarioRequest) -> UsuarioResponse:
        """
        Orquestra a criação do operador:
        1. Valida e normaliza o e-mail através do Value Object.
        2. Valida se o e-mail já está em uso na oficina.
        3. Gera o hash seguro da senha.
        4. Persiste e devolve o DTO estruturado.
        """
        # 1. Higienização e validação estrutural obrigatória do domínio
        try:
            email_vo = Email(command.email)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"E-mail inválido: {str(exc)}",
            )

        # 2. Verifica duplicidade usando o e-mail 100% limpo e normalizado
        usuario_existente = await self.repository.buscar_por_email(email_vo.valor)
        if usuario_existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe um usuário cadastrado com este e-mail.",
            )

        # 3. Cria a entidade de Domínio com a criptografia segura e o e-mail tratado
        novo_usuario = Usuario(
            nome=command.nome,
            email=email_vo.valor,
            senha=gerar_hash_senha(command.senha),
            role=command.role,
        )

        # 4. Salva e commita as alterações
        usuario_salvo = await self.repository.salvar(novo_usuario)

        return UsuarioResponse.model_validate(usuario_salvo)
