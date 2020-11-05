# coding=utf-

from __future__ import print_function

import argparse
import logging
import os
import pickle

import sys
import select
import socket
import threading

import udt4py

from config import COMMANDS_SHUTDOWN_DENY, COMMANDS_SHUTDOWN_CONFIRM
from ccp.misc import buscar_endereco_lan, buscar_enderecos_globais

# import daemon

logger = logging.getLogger('ccpd')


class ThreadInfo:
    def __init__(
            self,
            thread,
            address,
            tcp_connection,
            udt_socket,
            udt_connection
    ):
        self.thread = thread
        self.address = address
        self.tcp_connection = tcp_connection
        self.udt_socket = udt_socket
        self.udt_connection = udt_connection


class FileServer:

    __thread_info_lock = threading.Lock()

    def __init__(self, _port):
        self.__host = '127.0.0.1'
        self.__port = _port

        # # Abre uma conexão TCP
        # self.__main_socket = socket.socket(
        #     socket.AF_INET,
        #     socket.SOCK_STREAM
        # )

        self.__main_socket = udt4py.UDTSocket()
        self.__main_socket.bind((self.__host, self.__port))
        # self.__main_socket.setblocking(False)

        # self.__poll = udt4py.UDTEpoll()
        # self.__poll.add(self.__main_socket)

        # Servidor está ativo quando começa a ouvir.
        # Serve para parar o loop principal quando for servidor estiver prestes a desligar.
        self.__is_active = False

        self.__open_threads = dict()

    @property
    def ip(self):
        return self.__host

    @property
    def port(self):
        return self.__port

    @property
    def socket(self):
        return self.__main_socket

    # @property
    # def poll(self):
    #     return self.__poll

    @property
    def is_active(self):
        """
        Retorna se o servidor está esperando novas conexões (ativo) ou não.
        """
        return self.__is_active

    def activate(self, *args, **kwargs):
        """
        O servidor só espera conexões novas se estiver ativo.
        """
        self.__is_active = True
        logger.debug('Servidor foi ativado.')

        self.__main_socket.listen(*args, **kwargs)
        logger.debug('Servidor está escutando.')

    def accept_connection(self):
        """
        Atende uma nova conexão na fila de espera.
        :return: None
        :rtype: NoneType
        """
        if not self.__is_active:
            print('Servidor não está ativo.')
        else:
            logger.info('Esperando nova conexão aparecer.')

            user_connection = None
            address = None
            while user_connection is None:
                try:
                    user_connection, address = self.__main_socket.accept()
                except udt4py.UDTException:
                    pass

            logger.info('Nova conexão estabelecida com %s.', address)

            send_thread = threading.Thread(
                target=self.__interact,
                args=(user_connection, address)
            )

            self.__add_to_open_threads(user_connection, address, send_thread)
            send_thread.start()

    def __add_to_open_threads(self, tcp_connection, address, thread):
        thread_info = ThreadInfo(
            thread=thread,
            address=address,
            tcp_connection=tcp_connection,
            udt_socket=None,
            udt_connection=None,
        )
        logger.debug('Esperando lock para adicionar thread %s.', thread_info)
        with self.__thread_info_lock:
            self.__open_threads[tcp_connection] = thread_info
        logger.debug('Thread adicionada às threads abertas.')

    def __interact(self, user_connection, address):
        """

        :param user_connection: Conexão UDT do usuário
        :type user_connection: udt4py.UDTSocket
        :param address:
        :return:
        """

        logger.debug('Responder conexão no endereço: %s', address)
        try:
            user_message_bytes = user_connection.recv(1024)
            user_message = pickle.loads(user_message_bytes)
            try:
                if user_message['mode'] == 'U':
                    self.__run_recv_file_interaction(user_connection, user_message)
                elif user_message['mode'] == 'D':
                    self.__run_send_file_interaction(user_connection, user_message)
                else:
                    self.__run_error_interaction(user_connection, user_message)
            except KeyError:
                logger.error('Não reconheço esse tipo de mensagem! Vou fechar a conexão.')
        finally:
            self.close_user_connection(user_connection)

    def __bind_and_listen_on_free_port(self, udt_socket, min_port, max_port=65535):
        udt_port = min_port + 1
        while udt_port <= max_port:
            try:
                udt_socket.bind((self.__host, udt_port))
                udt_socket.listen()
                return udt_port
            except udt4py.UDTException:
                udt_port += 1
        raise IOError("No free ports.")

    def __run_recv_file_interaction(self, connection, message):
        path = message['path']

    def __run_error_file_interaction(self, connection, message):
        path = message['path']

        logger.debug('Buscando arquivo para enviar: %s', path)

        if not os.path.exists(path):
            # Send 'File not found' message
            file_size = None
            response_text = '-1'
            response_status = 0
            logger.debug('Não encontrei o arquivo %s', path)
        else:
            # Send 'Found <size>' message
            file_size = os.path.getsize(path)
            response_text = str(file_size)
            response_status = 1
            logger.debug('Encontrei o arquivo %s, que tem tamanho %d bytes', path, file_size)

        udt_socket = None
        free_port = None

        if response_status == 1:
            logger.info('Vou tentar criar socket UDT.')
            udt_socket = udt4py.UDTSocket()
            try:
                free_port = self.__bind_and_listen_on_free_port(
                    udt_socket,
                    min_port=self.__port
                )
            except IOError as exc:
                udt_socket = None
                response_text = f'UDT ERROR {exc}'
                response_status = 0
            else:
                with self.__thread_info_lock:
                    self.__open_threads[connection].udt_socket = udt_socket

                logger.info('UDT socket está ouvindo porta %d', free_port)

        response_msg = {
            'text': response_text,  # Incluir outros tipos de erro além de "Not found"
            'status': response_status,
            'port': free_port
        }
        logger.info('Mensagem para cliente: %s', response_msg)
        response_msg_bytes = pickle.dumps(response_msg)
        connection.send(response_msg_bytes)

        if udt_socket:
            logger.info("Agora que enviei mensagem ao cliente, eu espero a conexão UDT...")
            user_connection, addr = udt_socket.accept()
            with self.__thread_info_lock:
                self.__open_threads[connection].udt_connection = user_connection

            logger.info("Vou enviar arquivo %s de %d bytes", path, file_size)
            user_connection.sendfile(path)
            logger.info("Terminei de enviar o arquivo %s de %d bytes", path, file_size)

    def __run_send_file_interaction(self, connection, message):
        path = message['path']

        logger.debug('Buscando arquivo para enviar: %s', path)

        if not os.path.exists(path):
            # Send 'File not found' message
            file_size = None
            response_text = '-1'
            response_status = 0
            logger.debug('Não encontrei o arquivo %s', path)
        else:
            # Send 'Found <size>' message
            file_size = os.path.getsize(path)
            response_text = str(file_size)
            response_status = 1
            logger.debug('Encontrei o arquivo %s, que tem tamanho %d bytes', path, file_size)

        udt_socket = None
        free_port = None

        if response_status == 1:
            logger.info('Vou tentar criar socket UDT.')
            udt_socket = udt4py.UDTSocket()
            try:
                free_port = self.__bind_and_listen_on_free_port(
                    udt_socket,
                    min_port=self.__port
                )
            except IOError as exc:
                udt_socket = None
                response_text = f'UDT ERROR {exc}'
                response_status = 0
            else:
                with self.__thread_info_lock:
                    self.__open_threads[connection].udt_socket = udt_socket

                logger.info('UDT socket está ouvindo porta %d', free_port)

        response_msg = {
            'text': response_text,  # Incluir outros tipos de erro além de "Not found"
            'status': response_status,
            'port': free_port
        }
        logger.info('Mensagem para cliente: %s', response_msg)
        response_msg_bytes = pickle.dumps(response_msg)
        connection.send(response_msg_bytes)

        if udt_socket:
            logger.info("Agora que enviei mensagem ao cliente, eu espero a conexão UDT...")
            user_connection, addr = udt_socket.accept()
            with self.__thread_info_lock:
                self.__open_threads[connection].udt_connection = user_connection

            logger.info("Vou enviar arquivo %s de %d bytes", path, file_size)
            user_connection.sendfile(path)
            logger.info("Terminei de enviar o arquivo %s de %d bytes", path, file_size)

    def deactivate(self):
        """
        O servidor para de esperar por novas conexões.
        :return:
        """
        if self.__is_active:
            self.__is_active = False
            logger.debug('Servidor foi desativado e não atenderá mais conexões.')

    def wait_all_user_connections(self):
        """
        Desativa o loop principal de recebimento de conexões.
        Isso não impede que novas conexões sejam feitas em novas chamadas,
        apenas impede que o servidor seja desligado com conexões ativas.
        :return: None
        :rtype: NoneType
        """

        self.deactivate()  # Stops accepting new connections.

        # Since the server stopped accepting new connections, I only use lock to guarantee consistency.
        with self.__thread_info_lock:
            thread_infos = list(self.__open_threads.values())

        if len(thread_infos) == 1:
            logger.info('Esperando cliente %s terminar.', thread_infos[0].address)
        elif len(thread_infos) > 1:
            logger.info('Esperando clientes %s terminarem.', [info.address for info in thread_infos])

        logger.info('Aguardando término das conexões...')
        for info in thread_infos:
            connection_thread = info.thread
            connection_thread.join()

        logger.info('Todas as conexões terminaram.')

    def close_user_connection(self, tcp_connection):
        """
        Closes user's TCP connection to the server.
        :param tcp_connection: TCP connection
        :return: Nothing.
        """
        logger.debug('Esperando lock para fechar conexão %s.', tcp_connection)
        with self.__thread_info_lock:
            # Se não encontrar conexão, deve retornar erro!
            # connection_info = self.__open_connections[tcp_connection]
            # closed_connection_info = self.__convert_to_inactive_connection(connection_info)
            # self.__closed_connections.append(closed_connection_info)
            try:
                closed_thread_info = self.__open_threads.pop(tcp_connection)
            except KeyError:
                closed_thread_info = None

        logger.debug('Fechei a conexão %s', tcp_connection)
        if closed_thread_info:
            tcp_connection = closed_thread_info.tcp_connection
            tcp_connection.close()

            udt_socket = closed_thread_info.udt_socket
            if udt_socket:
                udt_socket.close()

            udt_connection = closed_thread_info.udt_connection
            if udt_connection:
                udt_connection.close()

    def close_all_user_connections(self):
        """
        Termina forçosamente todas as conexões ativas.
        :return: None
        :rtype: NoneType
        """
        self.deactivate()  # Stops accepting new connections.

        # Since the server stopped accepting new connections, I only use lock to guarantee consistency.
        with self.__thread_info_lock:
            open_threads = list(self.__open_threads.items())

        for user_connection, thread_info in open_threads:
            # print('Fechando conexão:\n', thread_info)
            logger.info('Fechando conexão:\n%s', thread_info)
            self.close_user_connection(user_connection)

        logger.info('Todas as conexões foram terminadas.')

    @staticmethod
    def __confirm_shutdown():
        """
        Interação com o usuário para confirmar se desliga ou não a aplicação.
        :return: None
        :rtype: NoneType
        """
        while True:
            input_str = input('Deseja desligar o servidor com conexões ativas? (s/[n]): ').lower()
            if input_str in COMMANDS_SHUTDOWN_CONFIRM:
                print('Vou desligá-lo.')
                return True
            elif input_str in COMMANDS_SHUTDOWN_DENY:
                print('Não vou desligá-lo.')
                return False
            else:
                print('Responda Sim (s) ou Não (n).')

    def shutdown(self, wait=True, force=False):
        """
        Desliga o servidor, se certificando de que nenhuma thread foi deixada esperando.
        :param force: Desligar sem perguntar sobre threads esperando.
        :type: bool
        :param wait: Esperar para que todas as threads terminem elegantemente.
        :type: bool
        :return: Retorna se desligou, ou não.
        :rtype: bool
        """
        logger.debug('Desligando servidor wait = %s, force = %s', wait, force)

        if self.__open_threads and not force:
            logger.info('Vou confirmar antes de desligar.')
            confirmado = self.__confirm_shutdown()
            if not confirmado:
                return False

        if wait:
            self.wait_all_user_connections()
        else:
            self.close_all_user_connections()

        print('Desligando...')
        self.__main_socket.close()
        print('Servidor foi desligado.')

        return True

    # ------------------------------ Impressões ------------------------------ #

    # @staticmethod
    # def __connection_repr(info):
    #     """
    #     Retorna a string padrão para informações de conexão.
    #     :param info: Informação sobre conexão
    #     :type: collections.namedtuple
    #     :return: string padrão para informações da conexão
    #     :rtype: str
    #     """
    #     info_str = 'Conexão(endereço={}, início=<{}>, fim=<{}>, thread="{}")'
    #     return info_str.format(
    #         info.address,
    #         info.start_time.strftime('%Y-%m-%d %H:%M:%S'),
    #         info.end_time.strftime('%Y-%m-%d %H:%M:%S') if info.end_time else None,
    #         info.thread.name
    #     )
    #
    # def __listar_conexoes(self, conexoes):
    #     """
    #     Listagem de conexões.
    #     :param conexoes: Lista de informações de conexão.
    #     :type conexoes: List[ConnectionInfo]
    #     :return: Listagem
    #     :rtype: str
    #     """
    #     if not conexoes:
    #         conexoes_str = 'Nenhuma'
    #     else:
    #         conexoes_str = '\n'
    #         for idx, info in enumerate(conexoes):
    #             conexoes_str += ' - {}: {}\n'.format(idx, self.__connection_repr(info))
    #
    #     return conexoes_str
    #
    # def listar_conexoes_abertas(self):
    #     """
    #     Listagem de conexões abertas do servidor.
    #     :return: Listagem
    #     :rtype: str
    #     """
    #     conexoes = self.__open_connections.values()
    #
    #     response_str = 'Conexões abertas: '
    #     response_str += self.__listar_conexoes(conexoes)
    #
    #     return response_str
    #
    # def listar_conexoes_fechadas(self):
    #     """
    #     Listagem de conexões fechadas do servidor.
    #     :return: Listagem
    #     :rtype: str
    #     """
    #     conexoes = self.__closed_connections
    #
    #     response_str = 'Conexões fechadas: '
    #     response_str += self.__listar_conexoes(conexoes)
    #
    #     return response_str
    #
    # def listar_usuarios_ativos(self):
    #     """
    #     Pede ao (único) session acoplado pelos usuários ativos
    #     :return: Listagem de usuários ativos
    #     :rtype: str
    #     """
    #     return self.__session.listar_usuarios_ativos()


def show_server_info(server):
    info_str = (
        "~~~~~~Informações do servidor~~~~~\n"
        "Porta: {port}\n"
        "Endereço local: {local_addr}\n"
        "Endereço global: \n"
        " - IPv4: {global_ipv4}\n"
        " - IPv6: {global_ipv6}\n"
        "-----------------------------------------------------------------------"
    )
    local_addr = buscar_endereco_lan()
    global_addrs = buscar_enderecos_globais()
    if not global_addrs:
        global_ipv4 = global_ipv6 = 'Não há conexão de internet.'
    else:
        global_ipv4, global_ipv6 = global_addrs

    formatted_info_str = info_str.format(
        port=server.port,
        local_addr=local_addr,
        global_ipv4=global_ipv4,
        global_ipv6=global_ipv6,
    )

    return formatted_info_str


# def run_server(server):
#     # Servidor passa a esperar por novas conexões.
#     server.activate()
#
#     # Informações sobre o servidor
#     print(show_server_info(server))
#
#     read_inputs = [server.socket]
#     write_inputs = []
#     exception_inputs = []
#
#     try:
#         while server.is_active:
#
#             read_inputs, _, _ = select.select(read_inputs, write_inputs, exception_inputs)
#
#             for ready in read_inputs:
#                 # Se conexão principal recebeu mensagem,
#                 # espera-se que seja de autenticação.
#                 if ready == server.socket:
#                     logger.info('Nova conexão recebida.')
#                     server.accept_connection()
#
#     except EOFError:
#         logger.exception('\nEOFError!')
#         print('\nEOFError!')
#     except KeyboardInterrupt:
#         logger.exception('\nKeyboardInterrupt!')
#         print('\nKeyboardInterrupt!')
#     finally:
#         server.shutdown(force=True, wait=False)

def run_server(server):
    # Servidor passa a esperar por novas conexões.
    server.activate()

    # Informações sobre o servidor
    # print(show_server_info(server))

    read_inputs = [server.socket]
    write_inputs = []
    exception_inputs = []

    try:
        while server.is_active:
            # read_inputs, _, _, _ = server.poll.wait()
            read_inputs, _, _ = select.select(read_inputs, write_inputs, exception_inputs)
            for ready in read_inputs:
                # Se conexão principal recebeu mensagem,
                # espera-se que seja de autenticação.
                if ready == server.socket:
                    logger.info('Nova conexão recebida.')
                    server.accept_connection()

    except EOFError:
        logger.exception('\nEOFError!')
        print('\nEOFError!')
    except KeyboardInterrupt:
        logger.exception('\nKeyboardInterrupt!')
        print('\nKeyboardInterrupt!')
    finally:
        server.shutdown(force=True, wait=False)


def run():
    from ccp.argparsers import get_server_parser
    ccpd_argparser = get_server_parser()
    parsed_args = ccpd_argparser.parse_args(sys.argv[1:])

    port = parsed_args.port

    debug_mode = parsed_args.debug_mode
    if debug_mode:
        logger.setLevel(logging.DEBUG)

    logger.info(
        'Informação de servidor:\n'
        ' - Port: %d\n'
        ' - Debug mode: %s\n',
        port, debug_mode
    )

    try:
        file_server = FileServer(port)
    except OverflowError:
        print('Porta {} inválida. Ela deve pertencer a [0, 65535].'.format(port))
        sys.exit(1)
    else:
        logger.info('Servidor foi criado.')

    try:
        run_server(file_server)
    except Exception as err:
        print('De novo...', err)
        file_server.shutdown(wait=False, force=True)


if __name__ == '__main__':
    run()
