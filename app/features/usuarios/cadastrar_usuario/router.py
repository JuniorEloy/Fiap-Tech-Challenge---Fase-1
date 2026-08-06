from fastapi import APIRouter, Depends, status, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.infra.db.database import get_db
from app.shared.security.dependencies import require_roles
from app.shared.security.roles import Role
from app.shared.security.password import gerar_hash_senha
from app.features.autenticacao.models import Usuario

router = APIRouter(prefix="/usuarios", tags=["Gestão de Usuários"])


class CriarUsuarioRequest(BaseModel):
    nome: str
    email: EmailStr
    senha: str
    role: Role


@router.post("", status_code=status.HTTP_201_CREATED)
async def cadastrar_operador(
    body: CriarUsuarioRequest,
    db: AsyncSession = Depends(get_db),
    # Rota protegida exclusiva para Gerentes
    current_user=Depends(require_roles([Role.GERENTE])),
):
    res = await db.execute(select(Usuario).where(Usuario.email == body.email))
    if res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Já existe um usuário cadastrado com este e-mail.",
        )

    novo_usuario = Usuario(
        nome=body.nome,
        email=body.email,
        senha_hash=gerar_hash_senha(body.senha),
        role=body.role,
    )
    db.add(novo_usuario)
    await db.commit()
    await db.refresh(novo_usuario)

    return {
        "id": str(novo_usuario.id),
        "nome": novo_usuario.nome,
        "email": novo_usuario.email,
        "role": novo_usuario.role,
    }
