import os
import pathlib
import socket
from typing import Tuple


def parse_address(address: str) -> Tuple[str, int]:
    """
    Separa o endereço de entrada em IP e PORT.
    :param address: <IP>:<PORT>
    :return: (<IP>, <PORT>)
    """
    try:
        hostname, port_str = address.split(':')
        port = int(port_str)
    except ValueError:  # not enough values to unpack
        raise ValueError('Formato inválido de endereço. Use <IP>:<PORTA>')

    return hostname, port


def is_valid_ipv4_hostname(hostname: str) -> bool:
    """
    Verifica se endereço é IPv4 válido.
    :param hostname: Endereço IP
    :return: True se é válido, senão False.
    """
    # Fonte: https://stackoverflow.com/a/4017219
    try:
        socket.inet_pton(socket.AF_INET, hostname)
    except AttributeError:  # no inet_pton here, sorry
        try:
            socket.inet_aton(hostname)
        except socket.error:
            return False
        return hostname.count('.') == 3
    except socket.error:  # not a valid address
        return False

    return True


def is_valid_ipv6_hostname(hostname: str) -> bool:
    """
    Verifica se endereço é IPv6 válido.
    :param hostname: Endereço IP
    :return: True se é válido, senão False.
    """
    # Fonte: https://stackoverflow.com/a/4017219
    try:
        socket.inet_pton(socket.AF_INET6, hostname)
    except socket.error:  # not a valid address
        return False
    return True


def is_valid_port(port_number: int) -> bool:
    """
    Verifica se porta está no intervalo [0, 65536).
    :param port_number: Porta de conexão
    :return: True se é válida, senão False.
    """
    return port_number in range(0, 65536)


def validate_ip(hostname: str) -> str:
    """
    Termina programa se IP for inválido.
    :param hostname: Endereço IP
    """
    if (not is_valid_ipv4_hostname(hostname) and
            not is_valid_ipv6_hostname(hostname)):
        raise ValueError(f'IP {hostname} é inválido.')
    return hostname


def validate_port(port: int) -> int:
    """
    Termina programa se porta for inválida.
    :param port: Porta de conexão
    """
    if not is_valid_port(port):
        raise ValueError(f'Porta {port} é inválida.')
    return port


def get_abspath(path: str) -> str:
    """
    Monta caminho absoluto a partir de um dado caminho de arquivo.
    :param path: Caminho de um arquivo
    :return: Caminho absoluto do arquivo
    """
    base_path = pathlib.Path(__file__).parent
    abspath = (base_path / path).resolve()
    return abspath


def validate_path(abs_path: str) -> str:
    """
    Termina programa se caminho absoluto for inválido, ou seja:
     -
    :param abs_path: Caminho absoluto do arquivo
    :return: Caminho absoluto do arquivo
    """
    if not abs_path:
        err_str = 'Caminho vazio.'
        raise ValueError(err_str)

    if (os.path.isdir(abs_path) or
            os.path.islink(abs_path) or
            os.path.ismount(abs_path)):
        err_str = f'Caminho "{abs_path}" já existe, e não é arquivo.'
        raise FileExistsError(err_str)

    local_path_directory, local_path_file = os.path.split(abs_path)
    if not local_path_file:
        err_str = 'Caminho de arquivo vazio.'
        raise ValueError(err_str)

    # if (os.path.isdir(local_path_directory) or
    #         os.path.islink(local_path_directory) or
    #         os.path.ismount(local_path_directory)):
    #     err_str = f'Caminho "{local_path_directory}" já existe, e não é arquivo.'
    #     raise FileExistsError(err_str)

    if local_path_directory and not os.path.isdir(local_path_directory):
        err_str = f'Diretório "{local_path_directory}" não existe.'
        raise FileNotFoundError(err_str)

    if os.path.isfile(local_path_file):
        err_str = f'Arquivo {local_path_file} já existe.'
        raise FileExistsError(err_str)

    return abs_path


def get_partial_path(path: pathlib.Path, part_id: int) -> str:
    """
    Monta o caminho parcial, que é o caminho de parte de um arquivo inteiro.
    :param path: Caminho absoluto do arquivo-destino
    :param part_id: ID da partição
    :return: Caminho absoluto do arquivo-destino parcial
    """
    return str(path) + f'.part{part_id}'

    # target_directory, target_filename = os.path.split(path)
    # partial_target_filename = f'{port}_{target_filename}'
    # partial_path = target_directory + partial_target_filename
    # return partial_path
