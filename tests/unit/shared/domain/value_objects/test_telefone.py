import pytest
from app.shared.domain.value_objects.telefone import Telefone


def test_telefone_celular_valido_deve_instanciar_e_higienizar():
    """
    Cenário: Criação de telefone celular de 11 dígitos com máscara.
    Resultado esperado: Valor limpo de 11 dígitos e formato de exibição nacional correto.
    """
    telefone_mascara = "(11) 98765-4321"
    telefone_vo = Telefone(telefone_mascara)

    assert telefone_vo.valor == "11987654321"
    assert telefone_vo.formatado == "(11) 98765-4321"
    assert str(telefone_vo) == "(11) 98765-4321"


def test_telefone_fixo_valido_deve_instanciar_e_higienizar():
    """
    Cenário: Criação de telefone fixo de 10 dígitos com máscara.
    Resultado esperado: Valor limpo de 10 dígitos e formato de exibição nacional correto.
    """
    telefone_mascara = "  11-3456-7890  "
    telefone_vo = Telefone(telefone_mascara)

    assert telefone_vo.valor == "1134567890"
    assert telefone_vo.formatado == "(11) 3456-7890"
    assert str(telefone_vo) == "(11) 3456-7890"


@pytest.mark.parametrize(
    "telefone_invalido",
    [
        "",  # Vazio
        "   ",  # Apenas espaços
        "119876543",  # Apenas 9 dígitos (falta o DDD ou número incompleto)
        "119876543210",  # 12 dígitos (excedente)
        "(011) 98765-4321",  # DDD iniciado com zero (011)
        "abc-defg-hij",  # Sem números válidos
    ],
)
def test_telefone_invalido_deve_lancar_value_error(telefone_invalido: str):
    """
    Cenário: Tentativa de criação de telefone com formatos incorretos ou quantidade inválida de dígitos.
    Resultado esperado: Lançamento de ValueError.
    """
    with pytest.raises(ValueError) as exc_info:
        Telefone(telefone_invalido)

    # Pegamos a mensagem real do erro gerado
    mensagem_erro = str(exc_info.value)

    # Validamos se a mensagem é alguma das que a sua classe de fato produz
    assert (
        "O telefone não pode ser vazio" in mensagem_erro
        or "O telefone com DDD deve possuir 10 ou 11 dígitos numéricos" in mensagem_erro
        or "O código de DDD do telefone não pode iniciar com 0" in mensagem_erro
    )


def test_telefones_valores_iguais_devem_ser_considerados_iguais():
    """
    Cenário: Comparação de dois telefones com máscaras diferentes mas mesmos dígitos de domínio.
    Resultado esperado: Retorno True na comparação de igualdade (__eq__).
    """
    tel_a = Telefone("(11) 98888-7777")
    tel_b = Telefone("11988887777")

    assert tel_a == tel_b
