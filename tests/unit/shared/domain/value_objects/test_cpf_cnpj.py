import pytest

from app.shared.domain.value_objects.cpf_cnpj import CpfCnpj


class TestCpfCnpj:
    # ---------------------------------------------------------
    # CPF
    # ---------------------------------------------------------

    @pytest.mark.parametrize(
        "documento, esperado",
        [
            ("52998224725", "52998224725"),
            ("529.982.247-25", "52998224725"),
            (" 529.982.247-25 ", "52998224725"),
        ],
    )
    def test_deve_aceitar_cpf_valido(self, documento, esperado):
        vo = CpfCnpj(documento)

        assert vo.valor == esperado

    @pytest.mark.parametrize(
        "documento",
        [
            "12345678900",
            "11111111111",
            "22222222222",
            "52998224726",
        ],
    )
    def test_deve_rejeitar_cpf_invalido(self, documento):
        with pytest.raises(ValueError, match="CPF"):
            CpfCnpj(documento)

    # ---------------------------------------------------------
    # CNPJ NUMÉRICO
    # ---------------------------------------------------------

    @pytest.mark.parametrize(
        "documento, esperado",
        [
            ("11444777000161", "11444777000161"),
            ("11.444.777/0001-61", "11444777000161"),
            (" 11.444.777/0001-61 ", "11444777000161"),
        ],
    )
    def test_deve_aceitar_cnpj_numerico_valido(
        self,
        documento,
        esperado,
    ):
        vo = CpfCnpj(documento)

        assert vo.valor == esperado

    @pytest.mark.parametrize(
        "documento",
        [
            "11444777000100",
            "00000000000000",
            "11111111111111",
            "11444777000162",
        ],
    )
    def test_deve_rejeitar_cnpj_numerico_invalido(self, documento):
        with pytest.raises(ValueError, match="CNPJ"):
            CpfCnpj(documento)

    # ---------------------------------------------------------
    # CNPJ ALFANUMÉRICO
    # ---------------------------------------------------------

    @pytest.mark.parametrize(
        "documento, esperado",
        [
            ("NJMPE64V000121", "NJMPE64V000121"),
            ("NJ.MPE.64V/0001-21", "NJMPE64V000121"),
            ("nj.mpe.64v/0001-21", "NJMPE64V000121"),
        ],
    )
    def test_deve_aceitar_cnpj_alfanumerico_valido(
        self,
        documento,
        esperado,
    ):
        vo = CpfCnpj(documento)

        assert vo.valor == esperado

    @pytest.mark.parametrize(
        "documento",
        [
            "NJ.MPE.64V/0001-22",
            "NJMPE64V000122",
            "AA.AAA.AAA/AAAA-AA",
        ],
    )
    def test_deve_rejeitar_cnpj_alfanumerico_invalido(self, documento):
        with pytest.raises(ValueError, match="CNPJ"):
            CpfCnpj(documento)

    # ---------------------------------------------------------
    # HIGIENIZAÇÃO
    # ---------------------------------------------------------

    @pytest.mark.parametrize(
        "documento, esperado",
        [
            ("529.982.247-25", "52998224725"),
            ("11.444.777/0001-61", "11444777000161"),
            ("NJ.MPE.64V/0001-21", "NJMPE64V000121"),
            ("nj-mpe/64v.0001-21", "NJMPE64V000121"),
        ],
    )
    def test_deve_remover_caracteres_especiais(
        self,
        documento,
        esperado,
    ):
        vo = CpfCnpj(documento)

        assert vo.valor == esperado

    def test_deve_converter_letras_para_maiusculo(self):
        vo = CpfCnpj("nj.mpe.64v/0001-21")

        assert vo.valor == "NJMPE64V000121"

    # ---------------------------------------------------------
    # TAMANHO / FORMATO
    # ---------------------------------------------------------

    @pytest.mark.parametrize(
        "documento",
        [
            "",
            None,
            "123",
            "1234567890",
            "123456789012",
            "1234567890123",
            "123456789012345",
        ],
    )
    def test_deve_rejeitar_documento_com_tamanho_invalido(
        self,
        documento,
    ):
        with pytest.raises(
            ValueError,
            match="O documento deve ser um CPF",
        ):
            CpfCnpj(documento)

    # ---------------------------------------------------------
    # VALUE OBJECT
    # ---------------------------------------------------------

    def test_deve_ser_immutavel(self):
        vo = CpfCnpj("52998224725")

        with pytest.raises(AttributeError):
            vo.valor = "11111111111"

    # ---------------------------------------------------------
    # CASOS DE BORDA
    # ---------------------------------------------------------

    def test_deve_remover_caracteres_especiais_durante_higienizacao(self):
        vo = CpfCnpj("NJ@MPE#64V/0001-21")

        assert vo.valor == "NJMPE64V000121"

    def test_deve_aceitar_documento_com_apenas_espacos_ao_redor(self):
        vo = CpfCnpj("   529.982.247-25   ")

        assert vo.valor == "52998224725"

    def test_deve_rejeitar_documento_apenas_com_caracteres_especiais(self):
        with pytest.raises(ValueError):
            CpfCnpj("@#$%¨&*()-_/.")

    def test_deve_rejeitar_documento_apenas_com_letras(self):
        with pytest.raises(ValueError):
            CpfCnpj("ABCDEFGHIJKLMN")

    def test_deve_aceitar_cpf_recebido_como_inteiro(self):
        vo = CpfCnpj(52998224725)

        assert vo.valor == "52998224725"

    def test_deve_rejeitar_booleano_como_documento(self):
        with pytest.raises(ValueError):
            CpfCnpj(True)

    def test_deve_rejeitar_lista_como_documento(self):
        with pytest.raises(ValueError):
            CpfCnpj(["52998224725"])

    def test_deve_rejeitar_dict_como_documento(self):
        with pytest.raises(ValueError):
            CpfCnpj({"cpf": "52998224725"})

    def test_deve_rejeitar_objeto_vazio(self):
        with pytest.raises(ValueError):
            CpfCnpj(None)

    def test_deve_normalizar_letras_minusculas_em_cnpj_alfanumerico(self):
        vo = CpfCnpj("nj.mpe.64v/0001-21")

        assert vo.valor == "NJMPE64V000121"

    def test_documento_deve_ser_string_apos_normalizacao(self):
        vo = CpfCnpj("529.982.247-25")

        assert isinstance(vo.valor, str)

    def test_deve_manter_documento_normalizado_apos_criacao(self):
        vo = CpfCnpj("11.444.777/0001-61")

        assert vo.valor == "11444777000161"

        with pytest.raises(AttributeError):
            vo.valor = "qualquer-coisa"

    @pytest.mark.parametrize(
        "documento",
        [
            "52998224725",
            "11444777000161",
            "NJMPE64V000121",
        ],
    )
    def test_documento_valido_sem_mascara_nao_deve_ser_alterado(
        self,
        documento,
    ):
        vo = CpfCnpj(documento)

        assert vo.valor == documento
