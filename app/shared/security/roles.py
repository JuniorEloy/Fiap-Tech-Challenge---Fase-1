from enum import Enum


class Role(str, Enum):
    CLIENTE = "CLIENTE"
    RECEPCIONISTA = "RECEPCIONISTA"
    MECANICO = "MECANICO"
    ESTOQUISTA = "ESTOQUISTA"
    GERENTE = "GERENTE"
