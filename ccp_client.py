import argparse
import logging
import os
import pathlib
import socket
import sys
import pickle
from typing import List, Tuple, Dict
import threading

import tqdm


def get_client_parser() -> argparse.ArgumentParser:
    """
    Leitor de argumentos da aplicação cliente.
     - address: Endereço do servidor
     - local: Caminho do arquivo-destino (local)
     - remote: Caminho do arquivo-fonte (remoto)
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


def validate_port(port: int) -> port:
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
    Termina programa se caminho absoluto for inválido.
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


def send_request(connection: socket.socket, request: Dict):
    """
    Envia requisição ao servidor
    :param connection: Conexão com servidor
    :param request: Pedido
    """
    request_bytes = pickle.dumps(request)
    connection.sendall(request_bytes)


def recv_response(connection: socket.socket) -> Dict:
    """
    Recebe resposta do servidor
    :param connection: Conexão com servidor
    :return: Resposta do servidor
    """
    end_byte = None
    message_bytes = b''
    while end_byte != '\0':
        recv_bytes = connection.recv(1024)
        message_bytes += recv_bytes
        end_byte = message_bytes[-1]

    message = pickle.loads(message_bytes)
    return message


def get_partial_path(path: str, port: int) -> str:
    """
    Monta o caminho parcial, que é o caminho de parte de um arquivo inteiro.
    :param path: Caminho absoluto do arquivo-destino
    :param port: Porta usada pelo servidor para enviar essa parte
    :return: Caminho absoluto do arquivo-destino parcial
    """
    target_directory, target_filename = os.path.split(path)
    partial_target_filename = f'{port}_{target_filename}'
    partial_path = target_directory + partial_target_filename
    return partial_path


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
        while (recv_bytes := download_socket.recv(BUFFER_SIZE)) != '\0':
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


def run_client(
        server_hostname: str,
        server_port: int,
        local_path: str,
        remote_path: str,
        streams: int,
        compressed: bool
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
    """

    if is_valid_ipv4_hostname(server_hostname):
        socket_family = socket.AF_INET
    elif is_valid_ipv6_hostname(server_hostname):
        socket_family = socket.AF_INET6
    else:
        raise ValueError(f'IP {server_hostname} não é válido para IPv4 ou IPv6')

    sock = socket.socket(socket_family, socket.SOCK_STREAM)
    sock.connect((server_hostname, server_port))

    # Agora que cliente se conectou, ele envia o pedido de download.
    download_request = {
        'path': local_path,
        'streams': streams,
        'compressed': compressed
    }
    send_request(sock, download_request)

    download_response = recv_response(sock)
    download_ports = download_response['ports']
    if download_ports is None:
        print(f'Arquivo {remote_path} não foi encontrado pelo servidor.')
        sys.exit(1)

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

    join_downloaded_files(local_path, download_ports)
    print('Fim!')


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
