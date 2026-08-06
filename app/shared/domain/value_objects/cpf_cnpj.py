import re
from dataclasses import dataclass
from validate_docbr import CNPJ, CPF


@dataclass(frozen=True)
class CpfCnpj:
    valor: str

    def __post_init__(self):
        if self.valor is not None and (
            isinstance(self.valor, bool) or not isinstance(self.valor, (str, int))
        ):
            raise ValueError("CPF/CNPJ deve ser informado como texto ou número.")

        doc_limpo = re.sub(r"[^a-zA-Z0-9]", "", str(self.valor or "")).strip().upper()

        object.__setattr__(self, "valor", doc_limpo)

        self._validar()

    def _validar(self):
        # Validação de CPF (11 dígitos)
        if len(self.valor) == 11:
            cpf_validator = CPF()
            if not cpf_validator.validate(self.valor):
                raise ValueError(f"CPF '{self.valor}' é inválido.")

        # Validação de CNPJ (14 caracteres/dígitos)
        elif len(self.valor) == 14:
            cnpj_validator = CNPJ()
            if not cnpj_validator.validate(self.valor):
                raise ValueError(f"CNPJ '{self.valor}' é inválido.")

        else:
            raise ValueError(
                "O documento deve ser um CPF (11 dígitos) ou CNPJ (14 caracteres)."
            )

    @property
    def formatado(self) -> str:
        """
        Retorna o CPF ou CNPJ formatado de forma legível (com pontos, traço e barra).
        Exemplos de retorno:
          - CPF:  123.456.789-01
          - CNPJ: 12.345.678/0001-90
        """
        if len(self.valor) == 11:
            return (
                f"{self.valor[:3]}.{self.valor[3:6]}.{self.valor[6:9]}-{self.valor[9:]}"
            )
        elif len(self.valor) == 14:
            return f"{self.valor[:2]}.{self.valor[2:5]}.{self.valor[5:8]}/{self.valor[8:12]}-{self.valor[12:]}"
        return self.valor
