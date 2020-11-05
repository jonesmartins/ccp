import logging
import socketserver
import pickle
import os
import threading
import socket
import sys
import gzip
import psutil
import daemon
import math
from datetime import datetime


from messaging import send_message, recv_message
from addressing import get_abspath, validate_path
from argparsers import get_server_parser
from utils import bytes2human, human2bytes


def get_partition_sizes(size, n_workers):
    division, remainder = divmod(size, n_workers)
    return [division + 1 for _ in range(remainder)] + [division for _ in range(n_workers - remainder)]


class ThreadedFileServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


class ThreadedFileServerRequestHandler(socketserver.BaseRequestHandler):
    def start_download(
            self,
            sock,
            path,
            partition_index,
            block_size,
            partition_size,
            compressed
    ):
        connection, _ = sock.accept()
        try:
            with open(path, mode='rb') as file:
                file.seek(partition_index * partition_size)
                total_bytes_read = 0
                partition = 0
                while total_bytes_read < partition_size:
                    # with open(compressed_filename, 'w') as zf:
                    block_bytes = file.read(block_size)
                    if compressed:
                        block_bytes = gzip.compress(block_bytes, compresslevel=1)

                    connection.sendall(block_bytes)

                    print(f'{datetime.now()} - Bytes read: {len(block_bytes)}')
                    total_bytes_read += len(block_bytes)
                    print(
                        f'{datetime.now()} - Total bytes read: {total_bytes_read} bytes.')
                    partition += 1
                    print(f'{datetime.now()} - Total partitions:', partition)
            connection.shutdown(socket.SHUT_RDWR)

        except:
            pass
        else:
            print('Finished sending!')
        finally:
            connection.close()
            sock.close()

    def download_interaction(
            self,
            path: str,
            streams: int,
            compressed: bool,
    ):
        abs_path = get_abspath(path)
        validate_path(abs_path)

        logging.debug('Caminho absoluto do arquivo pedido: %s', abs_path)

        if not os.path.exists(abs_path):
            logging.debug('Arquivo %s não existe!', abs_path)
            server_response = {
                'ports': None,
                'size': None
            }
            send_message(
                connection=self.request,
                message=server_response
            )
            logging.debug('Enviei ao cliente mensagem de erro.')
            return None  # Termina conexão.

        file_size = os.path.getsize(abs_path)
        print(f'Tamanho do arquivo {abs_path}: {bytes2human(file_size)}.')

        def create_and_bind_socket():
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(('localhost', 0))
            s.listen(1)
            return s

        # Order sockets by port
        download_sockets = sorted(
            [create_and_bind_socket() for _ in range(streams)],
            key=lambda sock: sock.getsockname()[1]
        )

        # Particiona tamanho do arquivo em N streams.
        partition_sizes = get_partition_sizes(file_size, streams)
        assert sum(partition_sizes) == file_size
        logging.debug(
            'Tamanho das partições: %s',
            [bytes2human(size) for size in partition_sizes]
        )

        free_ram = psutil.virtual_memory().free
        logging.debug('Memória RAM disponível: %s', bytes2human(free_ram))


        # if blocksize is None:
        # print('Block size: max. partition size.')
        blocksizes = [free_ram // (2 * streams) for _ in partition_sizes]
        # else:
        #     blocksizes = [human2bytes(blocksize) for _ in partition_sizes]

        logging.debug(
            'Tamanho dos blocos: %s',
            [bytes2human(size) for size in blocksizes]
        )

        # total_blocks_read = math.ceil(
        #     sum(ps / bs for ps, bs in zip(partition_sizes, blocksizes))
        # )
        # print(f'Total blocks read: {total_blocks_read}')

        process_memory = free_ram // streams
        logging.debug('Memória por conexão: %s', bytes2human(process_memory))

        threads = []
        for i in range(streams):
            block_size = blocksizes[i]
            partition_size = partition_sizes[i]
            download_socket = download_sockets[i]
            thread = threading.Thread(
                target=self.start_download,
                args=(
                    download_socket,
                    abs_path,
                    i,
                    block_size,
                    partition_size,
                    compressed
                )
            )
            threads.append(thread)

        for thread in threads:
            thread.start()

        # Para garantir que não exista timeout por parte do cliente,
        # eu só aviso sobre as portas após criar as threads de download.
        server_response = {
            'size': file_size,
            'ports': [sock.getsockname()[1] for sock in download_sockets]
        }
        logging.debug(
            'Avisando ao cliente sobre as %d conexões criadas.',
            streams
        )
        send_message(
            connection=self.request,
            message=server_response
        )

        for thread in threads:
            thread.join()

        print('Fim da conexão com cliente.')

    def handle(self):
        logging.debug('Opa!')
        request_message = recv_message(connection=self.request)
        logging.debug('Mensagem recebida do cliente: %s', request_message)
        path = request_message['path']
        compressed = request_message['compressed']
        streams = request_message['streams']

        self.download_interaction(path, streams, compressed)


def run():
    parser = get_server_parser()
    parsed_args = parser.parse_args(sys.argv[1:])

    port = parsed_args.port

    debug_mode = parsed_args.debug_mode
    if debug_mode:
        logging.basicConfig(
            level=logging.DEBUG
        )
        logging.debug('Modo de depuração está ativado.')

    try:
        file_server = ThreadedFileServer(
            ('localhost', port),
            ThreadedFileServerRequestHandler
        )
    except OverflowError:
        print(f'Porta {port} inválida. Ela deve pertencer a [0, 65535].')
        sys.exit(1)
    else:
        print(
            '-----------------------------------------------------------\n'
            f'Servidor de arquivos ouvindo na porta {port}\n'
            '-----------------------------------------------------------\n'
        )

    # with daemon.DaemonContext():
    try:
        with file_server:
            file_server.serve_forever()

    except KeyboardInterrupt:
        print('\nKeyboardInterrupt!')
    except EOFError:
        print('\nEOFError!')
    finally:
        print('\nDesligando servidor...')
        file_server.shutdown()


if __name__ == '__main__':
    run()



