import argparse
import logging
import os
import pathlib
import pickle
import socket
import sys
import threading
from typing import List, Tuple, Dict

import tqdm

from addressing import (
    get_partial_path,
    is_valid_ipv4_hostname,
    is_valid_ipv6_hostname,
    parse_address,
    get_abspath,
    validate_path
)

from messaging import (
    send_message,
    recv_message
)

from utils import bytes2human, human2bytes
from argparsers import get_client_parser


def start_download(hostname: str, port: int, target_path: str):
    """
    Inicia o download de parte do arquivo até receber byte de término.
    :param hostname: IP do servidor
    :param port: Porta de envio do servidor
    :param target_path: Caminho absoluto do arquivo-destino
    """
    partial_path = get_partial_path(target_path, port)

    download_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    download_socket.connect((hostname, port))

    BUFFER_SIZE = 1024

    total_data_written = 0
    with open(partial_path, 'wb') as partial_file:
        while (recv_bytes := download_socket.recv(BUFFER_SIZE)):
            curr_data_written = partial_file.write(recv_bytes)
            total_data_written += curr_data_written
    print(f'Fim do download. Baixei {total_data_written} bytes.')


def join_downloaded_files(target_path: str, ports: List[int], read_size=2**20):
    partial_paths = [
        get_partial_path(target_path, port)
        for port in ports
    ]

    total_downloaded_bytes = sum(
        os.path.getsize(path) for path in partial_paths
    )

    progress_bar = tqdm.tqdm(
        total_downloaded_bytes,
        f"Juntando {len(ports)} arquivos, totalizando {total_downloaded_bytes} bytes.",
        unit="B",
        unit_scale=True,
        unit_divisor=read_size
    )
    with open(target_path, 'wb') as complete_file:
        for path in partial_paths:
            with open(path, 'rb') as partial_file:
                read_bytes = partial_file.read(read_size)
                curr_data_written = complete_file.write(read_bytes)
                progress_bar.update(curr_data_written)


def confirm_decision(question):
    print(question)
    while True:
        lower = input('([S]/N) >> ').lower()
        if lower in {'', 's', 'sim'}:
            return True
        elif lower in {'n', 'nao', 'não'}:
            return False
        else:
            print('Por favor, confirme (s, sim) ou negue (n, nao, não).')


def run_client(
        server_hostname: str,
        server_port: int,
        local_path: str,
        remote_path: str,
        streams: int,
        compressed: bool,
        ask_confirmation=True,
):
    """
    Protocolo:
     - Cliente abre conexão com servidor.
     - Cliente pede arquivo <remote_path> ao servidor.
     - Cliente recebe tamanho de <remote_path> em bytes e P portas de conexão.
     - Cliente abre P portas de conexão com servidor, e salva os arquivos
        usando o nome <porta>_<local_path>.
     - Ao terminar todos os downloads, o cliente concatena os bytes um.
        Arquivo remoto: A = 1234A
        Arquivos baixados: 1A, 2A, 3A, 4A
        (1A + 2A) = 12A
        (12A + 3A) = 123A
        (123A + 4A) = 1234A = A
     - Fim.

    :param confirm_download:
    :param server_hostname: IP do servidor
    :param server_port: Porta do servidor
    :param local_path: Caminho do arquivo local
    :param remote_path: Caminho do arquivo remoto
    :param streams: Conexões paralelas
    :param compressed: Ativa compressão por parte do servidor
    :param ask_confirmation: Pede confirmação de download.
    """

    if is_valid_ipv4_hostname(server_hostname):
        socket_family = socket.AF_INET
    elif is_valid_ipv6_hostname(server_hostname):
        socket_family = socket.AF_INET6
    else:
        raise ValueError(f'IP {server_hostname} não é válido para IPv4 ou IPv6')

    logging.debug('Socket é da família %s.', socket_family)
    sock = socket.socket(socket_family, socket.SOCK_STREAM)

    sock.connect((server_hostname, server_port))
    logging.debug(
        'Cliente se conectou ao servidor em (%s, %s)',
        server_hostname, server_port
    )

    # Agora que cliente se conectou, ele envia o pedido de download.
    download_request = {
        'path': remote_path,
        'streams': streams,
        'compressed': compressed
    }
    logging.debug(
        'Pedido de download do cliente:\n%s', download_request
    )
    send_message(sock, download_request)

    # E recebe informações de download do servidor
    download_response = recv_message(sock)
    logging.debug(
        'Mensagem de resposta do servidor:\n%s', download_response
    )

    download_ports = download_response['ports']
    download_uncompressed_size = download_response['size']
    if download_ports is None:
        print(f'Arquivo {remote_path} não foi encontrado pelo servidor.')
        sys.exit(1)

    if ask_confirmation:
        decision_str = (
            'CONFIRMANDO O DOWNLOAD:\n'
            f' - Caminho local (absoluto): "{local_path}"\n'
            f' - Caminho remoto: "{remote_path}"\n'
            f' - Tamanho descomprimido do arquivo remoto: {bytes2human(download_uncompressed_size)}\n'
            f' - Compressão: {"ativada" if compressed else "desativada"}\n'
            'Tem certeza que quer continuar?'
        )
        confirmed = confirm_decision(decision_str)
        if not confirmed:
            print('Tudo bem! Fechando conexão.')
            sock.close()
            sys.exit()

    threads = [
        threading.Thread(
            target=start_download,
            args=(server_hostname, port, local_path)
        )
        for port in download_ports
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    sock.close()
    join_downloaded_files(local_path, download_ports)
    print('Fim!')


def run():
    parser = get_client_parser()
    parsed_args = parser.parse_args(sys.argv[1:])


    server_address = parsed_args.server_address
    local_path = parsed_args.local_path.strip()
    remote_path = parsed_args.remote_path.strip()
    streams = parsed_args.streams
    compressed = parsed_args.compressed

    if parsed_args.debug_mode:
        logging.basicConfig(
            level=logging.DEBUG
        )
        logging.debug('Mensagens de depuração foram ativadas.')

    logging.debug('Argumentos recebidos: %s', parsed_args)

    server_hostname, server_port = parse_address(server_address)

    abs_local_path = get_abspath(local_path)
    validate_path(abs_local_path)

    run_client(
        server_hostname,
        server_port,
        local_path,
        remote_path,
        streams,
        compressed,
        ask_confirmation=True
    )


if __name__ == '__main__':
    run()
