import re


class Placa:
    """
    Value Object representando uma placa de veículo nacional.
    Suporta os formatos Tradicional (AAA-9999) e Mercosul (AAA9A99).
    """

    def __init__(self, valor: str):
        self._valor = self._higienizar_e_validar(valor)

    def _higienizar_e_validar(self, valor: str) -> str:
        if not valor:
            raise ValueError("A placa do veículo não pode ser vazia.")

        # Higieniza removendo hífens, espaços e forçando maiúsculas
        limpo = re.sub(r"[\s-]", "", valor).upper()

        # Padrão tradicional: ABC1234
        regex_tradicional = r"^[A-Z]{3}\d{4}$"
        # Padrão Mercosul: ABC1D23
        regex_mercosul = r"^[A-Z]{3}\d[A-Z]\d{2}$"

        if not (re.match(regex_tradicional, limpo) or re.match(regex_mercosul, limpo)):
            raise ValueError(
                "Placa inválida. Formato esperado: AAA-9999 ou Mercosul AAA9A99."
            )

        return limpo

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
