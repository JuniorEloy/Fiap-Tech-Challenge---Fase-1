import pytest

# Ajuste o import abaixo para o caminho real da sua classe Placa
# from app.shared.domain.value_objects.placa import Placa
from app.shared.domain.value_objects.placa import Placa


class TestPlacaValueObject:
    """Suíte de testes rigorosa para o Value Object Placa."""

    @pytest.mark.parametrize(
        "entrada, valor_esperado, formatada_esperada",
        [
            # Casos ideais
            ("ABC-1234", "ABC1234", "ABC-1234"),
            ("ABC1234", "ABC1234", "ABC-1234"),
            # Letras minúsculas
            ("abc-1234", "ABC1234", "ABC-1234"),
            ("abc1234", "ABC1234", "ABC-1234"),
            # Espaços e sujeiras ignoráveis
            ("A B C - 1 2 3 4", "ABC1234", "ABC-1234"),
            ("  ABC - 1234  ", "ABC1234", "ABC-1234"),
        ],
    )
    def test_deve_criar_placa_tradicional_com_sucesso(
        self, entrada: str, valor_esperado: str, formatada_esperada: str
    ):
        """Testa o instanciamento, higienização e formatação de placas tradicionais."""
        placa = Placa(entrada)

        assert placa.valor == valor_esperado
        assert placa.formatada == formatada_esperada

    @pytest.mark.parametrize(
        "entrada, valor_esperado, formatada_esperada",
        [
            # Casos ideais
            ("ABC1D23", "ABC1D23", "ABC1D23"),
            # Letras minúsculas
            ("abc1d23", "ABC1D23", "ABC1D23"),
            # Hifens e espaços indevidos (o VO deve limpar)
            ("ABC-1D23", "ABC1D23", "ABC1D23"),
            ("A B C 1 D 2 3", "ABC1D23", "ABC1D23"),
        ],
    )
    def test_deve_criar_placa_mercosul_com_sucesso(
        self, entrada: str, valor_esperado: str, formatada_esperada: str
    ):
        """Testa o instanciamento, higienização e formatação de placas Mercosul."""
        placa = Placa(entrada)

        assert placa.valor == valor_esperado
        assert placa.formatada == formatada_esperada

    @pytest.mark.parametrize(
        "entrada_invalida",
        [
            # Vazios
            "",
            "   ",
            None,
        ],
    )
    def test_nao_deve_permitir_placas_vazias_ou_nulas(self, entrada_invalida):
        """Garante que a inicialização falha se o valor for nulo ou vazio."""
        with pytest.raises(ValueError, match="A placa do veículo não pode ser vazia"):
            Placa(entrada_invalida)

    @pytest.mark.parametrize(
        "entrada_invalida",
        [
            # Tamanho incorreto
            "ABC-123",  # Curta
            "ABC-12345",  # Longa
            # Posição errada de letras/números (Tradicional)
            "123-ABCD",  # Números e letras invertidos
            "AB-C1234",  # Formato que quebra os 3 primeiros
            "AB1-C234",
            # Posição errada de letras/números (Mercosul)
            "ABC12D3",  # Letra na posição errada (deve ser a 5ª)
            "ABCD123",  # 4 letras seguidas
            "1BC1D23",  # Começa com número
            # Caracteres especiais não permitidos
            "ABC*1234",
            "ABC_1D23",
            "ABC@1234",
        ],
    )
    def test_nao_deve_permitir_placas_fora_do_padrao_nacional(self, entrada_invalida):
        """Testa a rejeição rigorosa através das Expressões Regulares."""
        with pytest.raises(ValueError, match="Placa inválida"):
            Placa(entrada_invalida)

    def test_placas_com_mesmo_valor_devem_ser_consideradas_iguais(self):
        """Testa o dunder method __eq__ para comparar dois VOs."""
        placa_1 = Placa("ABC-1234")
        placa_2 = Placa("abc1234")
        placa_3 = Placa("XYZ-9999")

        # Devem ser iguais (mesmo que a entrada original tenha sido diferente)
        assert placa_1 == placa_2

        # Devem ser diferentes
        assert placa_1 != placa_3

    def test_placa_nao_deve_ser_igual_a_outro_tipo_de_objeto(self):
        """Garante que comparar a placa com uma string retorna False."""
        placa = Placa("ABC-1234")

        assert placa != "ABC1234"
        assert placa != "ABC-1234"
        assert placa != 123456

    def test_representacao_da_placa_repr(self):
        """Testa o dunder method __repr__ para logs e depuração."""
        placa_tradicional = Placa("abc1234")
        placa_mercosul = Placa("abc1d23")

        assert repr(placa_tradicional) == "<Placa ABC-1234>"
        assert repr(placa_mercosul) == "<Placa ABC1D23>"
