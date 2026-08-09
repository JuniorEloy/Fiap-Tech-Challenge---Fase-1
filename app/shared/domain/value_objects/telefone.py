import re

class Telefone:
    """
    Value Object representando um telefone nacional (fixo ou celular) com DDD.
    Higieniza a entrada removendo formatações e valida a estrutura de 10 ou 11 dígitos.
    """
    def __init__(self, valor: str):
        self._valor = self._validar_e_higienizar(valor)

    def _validar_e_higienizar(self, valor: str) -> str:
        if not valor:
            raise ValueError("O telefone não pode ser vazio.")

        # Limpa todos os caracteres não numéricos
        numeros = re.sub(r'\D', '', valor)

        # Valida tamanho padrão (10 para fixos, 11 para celulares)
        if len(numeros) not in (10, 11):
            raise ValueError("O telefone com DDD deve possuir 10 ou 11 dígitos numéricos.")

        # Impede que o DDD inicie com o dígito zero
        if numeros[0] == '0':
            raise ValueError("O código de DDD do telefone não pode iniciar com 0.")

        return numeros

    @property
    def valor(self) -> str:
        return self._valor

    @property
    def formatado(self) -> str:
        """Formata o número limpo para exibição rica: (XX) XXXXX-XXXX ou (XX) XXXX-XXXX."""
        if len(self._valor) == 11:
            return f"({self._valor[:2]}) {self._valor[2:7]}-{self._valor[7:]}"
        return f"({self._valor[:2]}) {self._valor[2:6]}-{self._valor[6:]}"

    def __eq__(self, outro: object) -> bool:
        if not isinstance(outro, Telefone):
            return False
        return self._valor == outro._valor

    def __str__(self) -> str:
        return self.formatado

    def __repr__(self) -> str:
        return f"<Telefone {self.formatado}>"