import pytest
from app.shared.domain.value_objects.email import Email

def test_email_valido_deve_instanciar_e_higienizar_com_sucesso():
    """
    Cenário: Instanciação de e-mail válido com letras maiúsculas e espaços.
    Resultado esperado: E-mail higienizado em caixa baixa e sem espaços.
    """
    email_sujo = "   JoAo.SILVA@OficinaMecanica.com.BR   "
    email_vo = Email(email_sujo)
    
    assert email_vo.valor == "joao.silva@oficinamecanica.com.br"
    assert str(email_vo) == "joao.silva@oficinamecanica.com.br"


@pytest.mark.parametrize(
    "email_invalido",
    [
        "",                     # Vazio
        "   ",                  # Apenas espaços
        "joao",                 # Sem arroba e domínio
        "joao@",                # Sem domínio
        "joao@oficina",         # Sem TLD (.com, .com.br, etc.)
        "@oficina.com",         # Sem parte local (usuário)
        "joao.silva@oficina.",  # TLD incompleto
        "joao@.com"             # Domínio incompleto
    ]
)
def test_email_invalido_deve_lancar_value_error(email_invalido: str):
    """
    Cenário: Tentativa de criação de e-mail com formatos sintáticos inválidos.
    Resultado esperado: Lançamento de ValueError com mensagem descritiva.
    """
    with pytest.raises(ValueError) as exc_info:
        Email(email_invalido)
        
    assert "O endereço de e-mail não pode ser vazio." in str(exc_info.value) or "Endereço de e-mail inválido." in str(exc_info.value)


def test_emails_valores_iguais_devem_ser_considerados_iguais():
    """
    Cenário: Comparação de dois Value Objects de e-mail com mesmo valor conceitual.
    Resultado esperado: Retorno True na comparação de igualdade (__eq__).
    """
    email_a = Email("contato@oficina.com")
    email_b = Email("  CONTATO@oficina.com  ")
    
    assert email_a == email_b