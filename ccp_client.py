import argparse
import logging
import os
import pathlib
import socket
import sys
from typing import List, Tuple


def get_client_parser() -> argparse.ArgumentParser:
    """
    Leitor de argumentos da aplicação cliente.
     - address: Endereço do servidor
     - local: Endereço do arquivo-destino (local)
     - remote: Endereço do arquivo-fonte (remoto)
     - compressed: Ativa compressão de envio, mas não descomprime no recebimento.
     - streams: Quantidade de conexões paralelas de envio/recebimento.
     - debug_mode: Ativa mensagens de depuração.

    :return: Leitor de argumentos.
    """

    parser = argparse.ArgumentParser(
        prog='CCP',
        description='Download de arquivos comprimidos em paralelo',
    )

    parser.add_argument(
        type=str,
        dest='server_address',
        help='Endereço do servidor no formato <IP>:<PORTA>'
    )

    parser.add_argument(
        '-l', '--local',
        required=True,
        type=str,
        dest='local_path',
        help='Path do arquivo local'
    )

    parser.add_argument(
        '-r', '--remote',
        required=True,
        type=str,
        dest='remote_path',
        help='Path do arquivo remoto'
    )

    parser.add_argument(
        '-c', '--compressed',
        action='store_true',
        default=True,
        dest='compressed',
        help='Ativa compressão no envio, mas não descomprime no recebimento.'
    )

    parser.add_argument(
        '-s', '--streams',
        type=int,
        dest='streams',
        default=4,
        help='Quantidade de transferências de um arquivo em paralelo (padrão: 4)'
    )

    parser.add_argument(
        '-d', '--debug-mode',
        action='store_true',
        dest='debug_mode',
        help='Ativa mensagens de depuração'
    )

    return parser


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


def is_valid_ipv4_address(address: str) -> bool:
    """
    Verifica se endereço é IPv4 válido.
    :param address: Endereço IP
    :return: True se é válido, senão False.
    """
    # Fonte: https://stackoverflow.com/a/4017219
    try:
        socket.inet_pton(socket.AF_INET, address)
    except AttributeError:  # no inet_pton here, sorry
        try:
            socket.inet_aton(address)
        except socket.error:
            return False
        return address.count('.') == 3
    except socket.error:  # not a valid address
        return False

    return True


def is_valid_ipv6_address(address: str) -> bool:
    """
    Verifica se endereço é IPv6 válido.
    :param address: Endereço IP
    :return: True se é válido, senão False.
    """
    # Fonte: https://stackoverflow.com/a/4017219
    try:
        socket.inet_pton(socket.AF_INET6, address)
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


def validate_ip(hostname: str):
    """
    Termina programa se IP for inválido.
    :param hostname: Endereço IP
    """
    if (not is_valid_ipv4_address(hostname) and
            not is_valid_ipv6_address(hostname)):
        raise ValueError(f'IP {hostname} é inválido.')
    return hostname


def validate_port(port: int):
    """
    Termina programa se porta for inválida.
    :param port: Porta de conexão
    """
    if not is_valid_port(port):
        raise ValueError(f'Porta {port} é inválida.')
    return port


def get_abspath(path):
    base_path = pathlib.Path(__file__).parent
    abspath = (base_path / path).resolve()
    return abspath


def validate_path(abs_path: str):
    """
    Termina programa se endereço absoluto for inválido.
    :param abs_path: Endereço absoluto em um sistema de arquivos
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
    print(f'Diretório: "{local_path_directory}"\nArquivo: "{local_path_file}"')
    if not local_path_file:
        err_str = 'Caminho de arquivo vazio.'
        raise ValueError(err_str)

    if (os.path.isdir(local_path_directory) or
            os.path.islink(local_path_directory) or
            os.path.ismount(local_path_directory)):
        err_str = f'Caminho "{local_path_directory}" já existe, e não é arquivo.'
        raise FileExistsError(err_str)

    if (local_path_directory and
            os.path.isdir(local_path_directory) and
            not os.path.exists(local_path_directory)):
        err_str = f'Diretório "{local_path_directory}" não existe.'
        raise FileNotFoundError(err_str)

    if os.path.isfile(local_path_file):
        err_str = f'Arquivo {local_path_file} já existe.'
        raise FileExistsError(err_str)

    return abs_path


def run_client(
        server_hostname,
        server_port,
        local_path,
        remote_path,
        streams,
        compressed
):
    print('Ran client')
    return True


def run_app(args: List[str]):
    """
    Recebe os argumentos da linha de comando e os valida.
    :param args: Argumentos da linha de comando
    """
    parser = get_client_parser()
    parsed_args = parser.parse_args(args)

    server_address = parsed_args.server_address
    local_path = parsed_args.local_path.strip()
    remote_path = parsed_args.remote_path.strip()
    streams = parsed_args.streams
    compressed = parsed_args.compressed

    if parsed_args.debug_mode:
        logging.basicConfig(
            level=logging.DEBUG
        )

    server_hostname, server_port = parse_address(server_address)

    # Vou deixar isso para dar erro na criação de socket.
    # validate_ip(server_hostname)
    # validate_port(server_port)

    abs_local_path = get_abspath(local_path)
    validate_path(abs_local_path)

    run_client(
        server_hostname,
        server_port,
        local_path,
        remote_path,
        streams,
        compressed
    )


if __name__ == '__main__':
    run_app(sys.argv[1:])
