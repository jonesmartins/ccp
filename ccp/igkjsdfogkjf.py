import udt4py

import tqdm
import argparse 
import pickle
import socket
import sys
import logging
import select
from config import *
import re
import typing


logger = logging.getLogger('ccp')


def open_tcp_connection(host, port):
    s = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    logger.debug("Tentando conectar com TCP a (%s, %s)", host, port)
    s.connect((host, port))

    logger.debug('Conexão TCP com (%s, %s)', host, port)

    return s


def open_udt_connection(host, port):
    u = udt4py.UDTSocket()  # AF_INET, SOCK_STREAM

    logger.debug("Tentando conectar com UDT a (%s, %s)", host, port)
    u.connect((host, port))


    logger.debug('Conexão UDT com (%s, %s)', host, port)

    return u


def get_ccp_argparser():
    """
    Cria o interpretador de linha de comando que funciona para cliente ou servidor.

    :return: Objeto ArgumentParser que interpretará a linha de comando.
    """
    parser = argparse.ArgumentParser(
        prog='CCP',
        description='Envio e recebimento de arquivos comprimidos.'
    )

    parser.add_argument(
        '-l', '--local',
        required=True,
        type=str,
        dest='local_path',
        help='Nome do arquivo local'
    )

    parser.add_argument(
        '-r', '--remote',
        required=True,
        type=str,
        dest='remote_path',
        help='O endereço do servidor no modelo <IP>:<PORT>/<REMOTE_PATH>'
    )

    parser.add_argument(
        '--upload', '-U',
        action='store_true',
        dest='upload_mode',
        help='Modo upload (padrão: False)'
    )

    parser.add_argument(
        '--compress', '-c',
        action='store_true',
        dest='compress',
        help='Comprime envio'
    )

    parser.add_argument(
        '--streams', '-s',
        default=1,
        type=int,
        help='Quantidade de streams em paralelo'
    )

    parser.add_argument(
        '-d', '--debug',
        action='store_true',
        dest='debug_mode',
        help='Modo DEBUG de logging'
    )

    return parser


def send_download_request(s, path):
    send_request(s, path, upload_mode=False)


def send_upload_request(s, path):
    send_request(s, path, upload_mode=True)


def send_request(s, path, upload_mode):
    message = {
        'mode': 'U' if upload_mode else 'D',
        'path': path
    }
    message_bytes = pickle.dumps(message)
    s.sendall(message_bytes)


def recv_response(s):
    end_byte = b'\0'
    response_bytes = b''
    while True:
        recv_bytes = s.recv(1024)
        if recv_bytes == end_byte:
            break
        response_bytes += recv_bytes
    response = pickle.loads(response_bytes)
    return response


from datetime import datetime
import gzip


# def sendfile(path, offset, partition_size):
#
#
#     from datetime import datetime
#     logger.info(f'Process %d with partition_size %d', path, partition_size)
#     with open(path, mode='rb') as file:
#         file.seek(offset)
#
#         total_bytes_read = 0
#         partition = 0
#         while total_bytes_read < partition_size:
#             compressed_filename = f'zipped/file_{process_id}_{partition}.zip'
#             with gzip.open(compressed_filename, mode='wb', compresslevel=1) as zf:
#             # with open(compressed_filename, 'w') as zf:
#                 file_bytes = file.read(block_size)
#                 bytes_read = zf.write(file_bytes)
#
#                 print(f'{datetime.now()} - Bytes read: {bytes_read}.')
#                 total_bytes_read += bytes_read
#                 print(f'{datetime.now()} - Total bytes read: {total_bytes_read} bytes.')
#             partition += 1
#             print(f'{datetime.now()} - Total partitions:', partition)



import time

BUFFER_SIZE = 1024 ** 2
import os
def sendfile(sock, path):
    size = os.path.getsize(path)
    progress = tqdm.tqdm(range(size), f"Sending {size}", unit="B", unit_scale=True, unit_divisor=BUFFER_SIZE)
    end_byte = b'\0'
    total_data_written = 0
    with open(path, 'rb') as file:
        while total_data_written < size:
            file_bytes = file.read(BUFFER_SIZE)
            data_sent = sock.send(file_bytes)
            progress.update(data_sent)
            total_data_written += data_sent


def recvfile(sock, path, size):
    progress = tqdm.tqdm(range(size), f"Receiving {size}", unit="B", unit_scale=True, unit_divisor=BUFFER_SIZE)
    total_data_written = 0
    with open(path, 'wb') as file:
        while total_data_written < size:
            data = sock.recv(BUFFER_SIZE)
            curr_data_written = file.write(data)
            total_data_written += curr_data_written
            progress.update(curr_data_written)


def udt_recvfile(sock, path, size):
    progress = tqdm.tqdm(range(size), f"Receiving {size}", unit="B", unit_scale=True, unit_divisor=BUFFER_SIZE)
    total_data_written = 0
    buffer = bytearray(BUFFER_SIZE)
    bv = memoryview(buffer)
    with open(path, 'wb') as file:
        while total_data_written < size:
            sock.recv(bv)
            curr_data_written = file.write(bv.tobytes())
            total_data_written += curr_data_written
            progress.update(curr_data_written)


def parse_remote_path(path: str) -> typing.Optional[typing.Tuple[str, str, str]]:
    """
    Interpreta endereço remoto de envio.
    :param path: Endereço remoto de envio
    :return: (Host, Port, Path)
    """
    try:
        address_pattern = re.compile(
            r'([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}.[0-9]{1,3}):([0-9]{1,5})(/.*)'
        )
        group = re.search(address_pattern, path).groups()
    except AttributeError:
        group = None

    return group


def end_connection(s):
    s.close()
    print('Fim.')


def run_client(local_path, remote_path, upload_mode=False):
    """
    Executa aplicação para envio e recebimento de dados do servidor.
    :param local_path: Endereço do arquivo local
    :param remote_path: Endereço do arquivo remoto no formato <IP>:<PORTA>/<PATH>
    :param upload_mode: Se verdadeiro, envia arquivos para o servidor.
    """

    parsed_address = parse_remote_path(remote_path)
    if parsed_address is None:
        err_str = 'Endereço de servidor é no modelo <IP>:<PORT>.'
        logger.error(err_str)
        # print(err_str)
        sys.exit(1)

    remote_host, remote_port, remote_path = parsed_address
    remote_port = int(remote_port)

    logger.info(
        'Informações:\n'
        ' - Server IP: %s\n'
        ' - Server port: %d\n'
        ' - Local path: %s\n'
        ' - Server path: %s\n'
        ' - Upload mode: %s\n',
        remote_host, remote_port,
        local_path, remote_path,
        upload_mode
    )

    try:
        tcp_connection = open_tcp_connection(remote_host, remote_port)
    except ConnectionRefusedError:
        print('Conexão recusada: Servidor em ({}, {}) deve estar desligado.'.format(remote_host, remote_port))
        sys.exit(1)
    except OverflowError:
        print('Porta deve pertencer a [0, 65535].')
        sys.exit(1)

    try:
        send_request(tcp_connection, path=remote_path, upload_mode=upload_mode)
    except Exception as err:
        print(err)
        sys.exit(1)

    try:
        server_response = recv_response(tcp_connection)
        logger.info('Resposta do servidor: %s', server_response)
    except Exception as err:
        print(err)
        sys.exit(1)

    server_text = server_response['text']
    status = server_response['status']
    udt_port = server_response['port']
    if status != 1:
        logger.error('Erro no servidor: %s', server_text)
        tcp_connection.close()
        sys.exit(1)
    else:
        file_size = int(server_text.split()[-1])
        logger.info('Servidor vai enviar %s de tamanho %s bytes.', remote_path, file_size)

    try:
        udt_connection = open_udt_connection(remote_host, udt_port)
        logger.info('Abri conexão UDT com (%s, %s)', remote_host, udt_port)
    except Exception as err:
        print(err)
        sys.exit(1)

    try:
        logger.info('Esperando receber por UDT o arquivo %s de tamanho %s do servidor em (%s, %s)', remote_path, file_size, remote_host, udt_port)
        udt_connection.recvfile(local_path, offset=0, size=file_size)
        # recvfile(tcp_connection, local_path, file_size)
    except Exception as err:
        print(err)
    finally:
        tcp_connection.close()
        # udt_connection.close()
        print('Fim.')


def run():
    ccp_argparser = get_ccp_argparser()

    parsed_args = ccp_argparser.parse_args(sys.argv[1:])

    local_path = parsed_args.local_path
    remote_path = parsed_args.remote_path
    upload_mode = parsed_args.upload_mode
    debug_mode = parsed_args.debug_mode

    if debug_mode:
        logging.basicConfig(
            level=logging.DEBUG
        )

    run_client(local_path, remote_path, upload_mode)


if __name__ == '__main__':
    run()




