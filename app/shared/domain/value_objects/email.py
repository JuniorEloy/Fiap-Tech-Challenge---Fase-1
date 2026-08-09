import re


class Email:
    """
    Value Object representando um endereço de e-mail válido.
    Garante immutabilidade, higienização de espaços e caixa baixa.
    """

    def __init__(self, valor: str):
        self._valor = self._validar_e_higienizar(valor)

    def _validar_e_higienizar(self, valor: str) -> str:
        if not valor:
            raise ValueError("O endereço de e-mail não pode ser vazio.")

        # Higieniza removendo espaços em branco extras e convertendo para minúsculas
        limpo = valor.strip().lower()

        # Regex padrão RFC 5322 simplificada de alta cobertura
        regex_email = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(regex_email, limpo):
            raise ValueError("Endereço de e-mail inválido.")

        return limpo

    @property
    def valor(self) -> str:
        return self._valor

    def __eq__(self, outro: object) -> bool:
        if not isinstance(outro, Email):
            return False
        return self._valor == outro._valor

    def __str__(self) -> str:
        return self._valor

    def __repr__(self) -> str:
        return f"<Email {self._valor}>"
