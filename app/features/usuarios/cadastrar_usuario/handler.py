from fastapi import HTTPException, status
from app.features.usuarios.models import Usuario
from app.features.usuarios.repository import UsuarioRepository
from app.features.usuarios.cadastrar_usuario.schemas import (
    CriarUsuarioRequest,
    UsuarioResponse,
)
from app.shared.security.password import gerar_hash_senha


class CadastrarUsuarioHandler:
    def __init__(self, repository: UsuarioRepository):
        self.repository = repository

    async def executar(self, command: CriarUsuarioRequest) -> UsuarioResponse:
        """
        Orquestra a criação do operador:
        1. Valida se o e-mail já está em uso na oficina.
        2. Gera o hash seguro da senha.
        3. Persiste e devolve o DTO estruturado.
        """
        # 1. Verifica duplicidade usando o repositório
        usuario_existente = await self.repository.buscar_por_email(command.email)
        if usuario_existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe um usuário cadastrado com este e-mail.",
            )

        # 2. Cria a entidade de Domínio com a criptografia segura
        novo_usuario = Usuario(
            nome=command.nome,
            email=command.email,
            senha=gerar_hash_senha(command.senha),
            role=command.role,
        )

        # 3. Salva e commita as alterações
        usuario_salvo = await self.repository.salvar(novo_usuario)

        return UsuarioResponse.model_validate(usuario_salvo)
