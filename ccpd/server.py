import logging
import socketserver
import pickle
import threading
import socket
import sys
import gzip
import psutil
import daemon
import os

from ccp.messaging import send_message, recv_message
from ccp.addressing import get_abspath
from ccp.argparsers import get_server_parser
from ccp.utils import bytes2human
from ccp.addressing import get_partial_path


def get_partition_sizes(size, n_workers):
    division, remainder = divmod(size, n_workers)
    return [division + 1 for _ in range(remainder)] + [division for _ in range(n_workers - remainder)]


class ThreadedFileServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


class ThreadedFileServerRequestHandler(socketserver.BaseRequestHandler):
    def compress_file(
            self,
            source_path: str,
            target_path: str,
            start_byte: int,
            partition_size: int
    ):
        """
        Comprime parte de um arquivo, salvando como target_path.
        :param source_path: Arquivo original
        :param target_path: Nome do arquivo particionado
        :param start_byte: Byte inicial
        :param partition_size: Tamanho da partição
        """
        print(
            f'Compressing {source_path} to {target_path} from {start_byte} to {start_byte + partition_size}.')
        with open(
                source_path,
                mode='rb'
        ) as file:
            file.seek(start_byte)
            with gzip.open(
                    target_path,
                    mode='wb',
                    compresslevel=1
            ) as gzip_file:
                bytes_written = gzip_file.write(file.read(partition_size))
                print(f'Wrote {bytes2human(bytes_written)} to {target_path}')

    def partition_file(
            self,
            source_path: str,
            target_path: str,
            start_byte: int,
            partition_size: int
    ):
        """
        Particiona um arquivo, salvando como target_path.
        :param source_path: Arquivo original
        :param target_path: Nome do arquivo particionado
        :param start_byte: Byte inicial
        :param partition_size: Tamanho da partição
        """
        print(f'Partitioning {source_path} to {target_path} from {start_byte} to {start_byte + partition_size}.')
        with open(
                source_path,
                mode='rb'
        ) as file:
            with open(
                    target_path,
                    mode='wb',
            ) as partitioned_file:
                file.seek(start_byte)
                bytes_written = partitioned_file.write(file.read(partition_size))
                print(f'Wrote {bytes2human(bytes_written)} to {target_path}')

    def send_partition(
            self,
            sock,
            partition_path,
            block_size
    ):
        """
        Envia arquivo.
        :param sock: Conexão TCP
        :param partition_path: Caminho do arquivo de partição
        :param block_size: Tamanho do bloco de envio
        """
        download_port = sock.getsockname()[1]

        connection, _ = sock.accept()

        # Antes de enviar o arquivo, enviamos o tamanho.
        file_size = os.path.getsize(partition_path)
        length_bytes = pickle.dumps(file_size)
        length_bytes_buf = bytearray(30)
        length_bytes_buf[:len(length_bytes)] = length_bytes
        connection.sendall(length_bytes_buf)

        print(
            f'{download_port}: Enviei o tamanho do arquivo parcial "{partition_path}": {bytes2human(file_size)}')

        try:
            with open(partition_path, mode='rb') as partial_file:
                total_bytes_read = 0
                blocks_written = 0
                while total_bytes_read < file_size:
                    block_bytes = partial_file.read(
                        min(file_size - total_bytes_read, block_size))
                    if not block_bytes:
                        raise RuntimeError(f'{download_port}: Read 0 bytes!')
                    print(
                        f'{download_port}: Li {bytes2human(len(block_bytes))} bytes de {partition_path} para enviar.')
                    connection.sendall(block_bytes)
                    print(f'{download_port}: Enviei block_bytes.')

                    total_bytes_read += len(block_bytes)
                    print(
                        f'{download_port}:  Total bytes read: {bytes2human(total_bytes_read)}.')
                    blocks_written += 1

        except Exception as exc:
            print(exc)
        else:
            print('Finished sending!')
        finally:
            connection.close()
            sock.close()

    def start_download(
            self,
            partition_id,
            sock,
            path,
            start_byte,
            partition_size,
            block_size,
            compressed
    ):

        partition_path = get_partial_path(
            path,
            part_id=partition_id
        )

        if compressed:
            self.compress_file(
                source_path=path,
                target_path=partition_path,
                start_byte=start_byte,
                partition_size=partition_size
            )
        else:
            self.partition_file(
                source_path=path,
                target_path=partition_path,
                start_byte=start_byte,
                partition_size=partition_size
            )

        info_str = (
            f'Send file whole: {path}\n'
            f' - start_byte: {start_byte}\n'
            f' - partition_size: {bytes2human(partition_size)}\n'
            f' - block_size: {bytes2human(block_size)}\n'
            f' - compressed: {compressed}\n'
            f'Result: {partition_path}\n'
        )
        print(info_str)

        self.send_partition(
            sock,
            partition_path,
            block_size=block_size
        )
        os.remove(partition_path)

    def download_interaction(
            self,
            path: str,
            streams: int,
            compressed: bool,
    ):
        """
        Interação de download após o pedido pelo cliente.
        :param path: Caminho do arquivo pedido
        :param streams: Número de conexões paralelas de envio
        :param compressed: Ativa compressão das partições
        """
        abs_path = get_abspath(path)

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
        start_byte = 0
        for i in range(streams):
            block_size = blocksizes[i]
            partition_size = partition_sizes[i]
            download_socket = download_sockets[i]
            thread = threading.Thread(
                target=self.start_download,
                args=(
                    i,
                    download_socket,
                    abs_path,
                    start_byte,
                    partition_size,
                    block_size,
                    compressed
                )
            )
            threads.append(thread)
            start_byte += partition_size

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
        """
        Recebe e reage ao pedido do cliente.
        """
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
        file_server.server_close()


if __name__ == '__main__':
    run()



