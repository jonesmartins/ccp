import argparse
import sys
import logging
from typing import List, Tuple
import os
import socket


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
        '-a', '--address',
        type=str,
        dest='server_address',
        help='Endereço do servidor no formato <IP>:<PORTA>'
    )

    parser.add_argument(
        '-l', '--local',
        type=str,
        dest='local_path',
        help='Path do arquivo local'
    )

    parser.add_argument(
        '-r', '--remote',
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
        help='Quantidade de transferências de um arquivo em paralelo'
    )

    parser.add_argument(
        '-d', '--debug-mode',
        action='store_true',
        dest='debug_mode',
        help='Ativa mensagens de depuração'
    )

    return parser


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
        print('Formato inválido de endereço. Use <IP>:<PORTA>')
        sys.exit(1)

    return hostname, port


def exit_if_invalid_ip(hostname: str):
    """
    Termina programa se IP for inválido.
    :param hostname: Endereço IP
    """
    if (not is_valid_ipv4_address(hostname) or
            not is_valid_ipv6_address(hostname)):
        print(f'IP {hostname} é inválido.')
        sys.exit(1)


def exit_if_invalid_port(port: int):
    """
    Termina programa se porta for inválida.
    :param port: Porta de conexão
    """
    if not is_valid_port(port):
        print(f'Porta {port} é inválida.')
        sys.exit(1)


def exit_if_invalid_path(path: str):
    """
    Termina programa se endereço for inválido.
    :param path: Endereço em um sistema de arquivos
    """
    local_path_directory, local_path_file = os.path.split(path)
    if not os.path.exists(local_path_directory):
        print(f'Diretório {local_path_directory} não existe.')
        sys.exit(1)

    if (os.path.isdir(local_path_file) or
            os.path.islink(local_path_file) or
            os.path.ismount(local_path_file)):
        print(f'{local_path_file} já existe, e não é arquivo.')
        sys.exit(1)

    if os.path.isfile(local_path_file):
        print(f'{local_path_file} já existe.')
        print('Por favor, renomeie para um arquivo inexistente.')
        sys.exit(1)


def run_client(
        server_hostname,
        server_port,
        local_path,
        remote_path,
        streams,
        compressed
):
    pass


def run_app(args: List[str]):
    """
    Recebe os argumentos da linha de comando e os valida.
    :param args: Argumentos da linha de comando
    """
    parser = get_client_parser()
    parsed_args = parser.parse_args(args)

    server_address = parsed_args.server_address
    local_path = parsed_args.local_path
    remote_path = parsed_args.remote_path
    streams = parsed_args.streams
    compressed = parsed_args.compressed

    # Ativa mensagens de depuração
    if parsed_args.debug_mode:
        logging.basicConfig(
            level=logging.DEBUG
        )

    server_hostname, server_port = parse_address(server_address)

    exit_if_invalid_ip(server_hostname)
    exit_if_invalid_port(server_port)
    exit_if_invalid_path(local_path)

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
