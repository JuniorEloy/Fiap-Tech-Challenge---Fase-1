import re


class Placa:
    """
    Value Object representando uma placa de veículo nacional.
    Suporta os formatos Tradicional (AAA-9999) e Mercosul (AAA9A99).
    """

    def __init__(self, valor: str):
        self._valor = self._higienizar_e_validar(valor)

    def _higienizar_e_validar(self, valor: str) -> str:
        if not valor or not str(valor).strip():
            raise ValueError("A placa do veículo não pode ser vazia.")

        # 1. Remove apenas os ESPAÇOS e deixa maiúsculo. MANTÉM o hífen para inspecionar!
        pre_limpo = re.sub(r"\s", "", str(valor)).upper()

        # 2. Expressões Regulares mais rigorosas (aceitam o hífen APENAS no lugar certo)
        # ^[A-Z]{3} = Começa com 3 letras
        # -?        = Pode ter zero ou um hífen (exatamente nesta posição)
        # \d{4}$    = Termina com 4 números
        regex_tradicional = r"^[A-Z]{3}-?\d{4}$"

        # O mesmo vale para o Mercosul: aceita ABC1D23 ou ABC-1D23
        regex_mercosul = r"^[A-Z]{3}-?\d[A-Z]\d{2}$"

        if not (
            re.match(regex_tradicional, pre_limpo)
            or re.match(regex_mercosul, pre_limpo)
        ):
            raise ValueError(
                "Placa inválida. Formato esperado: AAA-9999 ou Mercosul AAA9A99."
            )

        # 3. Agora que sabemos que a placa é válida e o hífen (se houver) está no lugar certo,
        # nós podemos removê-lo tranquilamente para armazenar o valor limpo (7 caracteres).
        return pre_limpo.replace("-", "")

    @property
    def valor(self) -> str:
        return self._valor

    @property
    def formatada(self) -> str:
        """Exibe a placa formatada com hífen se for o modelo tradicional."""
        # Como o VO garante que sempre tem 7 caracteres, olhamos a 5ª posição (índice 4).
        # Se for um número (ex: ABC1 2 34), é o modelo tradicional.
        if self._valor[4].isdigit():
            return f"{self._valor[:3]}-{self._valor[3:]}"

        # Se for Mercosul (ex: ABC1 D 23), retorna sem hífen.
        return self._valor

    def __eq__(self, outro: object) -> bool:
        if not isinstance(outro, Placa):
            return False
        return self._valor == outro._valor

    def __repr__(self) -> str:
        return f"<Placa {self.formatada}>"
