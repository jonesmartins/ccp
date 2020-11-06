import logging
import socket
import sys
import time
import threading

import tqdm

from ccp.addressing import (
    get_partial_path,
    is_valid_ipv4_hostname,
    is_valid_ipv6_hostname,
    parse_address,
    get_abspath,
    validate_path
)

from ccp.messaging import (
    send_message,
    recv_message
)

from ccp.utils import bytes2human
from ccp.argparsers import get_client_parser
from ccp.ccp_finish import join_downloaded_files


def start_download(
        hostname: str,
        port: int,
        partial_path: str
):
    """
    Inicia o download de parte do arquivo até receber byte de término.
    :param hostname: IP do servidor
    :param port: Porta de envio do servidor
    :param part_id: ID of partition
    :param target_path: Caminho absoluto do arquivo-destino
    """

    # print(f'{port}: Iniciando download de {target_path} para o arquivo parcial {partial_path}')

    download_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    download_socket.connect((hostname, port))

    file_length = recv_message(download_socket, nbytes=30)
    # print(f'{port}: Recebi tamanho do download: ', file_length)

    BUFFER_SIZE = 2 ** 20

    progress_bar = tqdm.tqdm(
        total=file_length,
        desc=f"Baixando {partial_path}.",
        unit="B",
        unit_scale=True,
        unit_divisor=BUFFER_SIZE
    )
    total_data_written = 0
    total_data_received = 0

    start = time.perf_counter()
    with progress_bar as p_bar:
        with open(partial_path, 'wb') as partial_file:
            while total_data_written < file_length:
                recv_bytes = download_socket.recv(BUFFER_SIZE)
                # print(f'{port}: Recebi {len(recv_bytes)} bytes do servidor.')
                if not recv_bytes or recv_bytes == 0:
                    raise RuntimeError('Broken connection')
                curr_data_written = partial_file.write(recv_bytes)
                total_data_written += curr_data_written
                total_data_received += len(recv_bytes)
                p_bar.update(n=len(recv_bytes))
        p_bar.refresh()

    end = time.perf_counter()
    print(
        f'Fim do download de {partial_path}.\n'
        f'Tamanho: {bytes2human(total_data_written)}.'
        f'Tempo: {(end - start):.5f} s'
    )


def confirm_decision(question):
    """
    Confirma determinada decisão.
    :param question: Pergunta ao usuário
    :return: Se confirmou, True, senão, False.
    """
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
        decompress: bool = False,
        ask_confirmation=True,
        keep_partitions=False
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

    :param server_hostname: IP do servidor
    :param server_port: Porta do servidor
    :param local_path: Caminho do arquivo local
    :param remote_path: Caminho do arquivo remoto
    :param streams: Conexões paralelas
    :param compressed: Ativa compressão por parte do servidor
    :param decompress: Descomprime após receber
    :param ask_confirmation: Pede confirmação de download
    :param keep_partitions: Mantém partições após união de arquivos
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

    partial_paths = [
        get_partial_path(local_path, part_id=i)
        for i in range(len(download_ports))
    ]

    threads = [
        threading.Thread(
            target=start_download,
            args=(
                server_hostname,
                port,
                partial_path,
                local_path
            )
        )
        for port, partial_path in zip(download_ports, partial_paths)
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    sock.close()

    # Se o download não foi comprimido, eu já junto as partições.
    if not compressed or (compressed and decompress):
        print('Juntando partições baixadas...')
        join_downloaded_files(partial_paths, local_path, keep_partitions)

    print('Fim!')


def run():
    parser = get_client_parser()
    parsed_args = parser.parse_args(sys.argv[1:])

    server_address = parsed_args.server_address
    local_path = parsed_args.local_path.strip()
    remote_path = parsed_args.remote_path.strip()
    streams = parsed_args.streams
    compressed = parsed_args.compressed
    keep_partitions = parsed_args.keep
    decompress = parsed_args.decompress

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
        decompress=decompress,
        ask_confirmation=True,
        keep_partitions=keep_partitions
    )


if __name__ == '__main__':
    run()
