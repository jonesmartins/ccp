import pickle
import socket
from typing import Dict


def send_message(connection: socket.socket, message):
    """
    Envia mensagem  de 512 bytes pela conexão para recv_message.
    :param connection: Conexão TCP
    :param message: Mensagem (pedido)
    """
    message_sendbuf = bytearray(512)
    request_bytes = pickle.dumps(message)
    message_sendbuf[:len(request_bytes)] = request_bytes
    connection.sendall(message_sendbuf)


def recv_n_bytes(
        connection: socket.socket,
        n_bytes: int,
        bufsize=1024
):
    empty_byte = b''
    message_bytes = b''
    total_bytes_received = 0
    while total_bytes_received < n_bytes:
        recv_bytes = connection.recv(min(n_bytes - total_bytes_received, bufsize))
        if recv_bytes == empty_byte:
            raise RuntimeError('Broken connection.')
        message_bytes += recv_bytes
        total_bytes_received += len(recv_bytes)

    message = pickle.loads(message_bytes)
    return message


def recv_message(connection: socket.socket, nbytes=512):
    """
    Recebe mensagem pela conexão enviada por send_message.
    :param connection: Conexão TCP
    :param nbytes: Tamanho esperado da mensagem
    :return: Mensagem
    """

    message = recv_n_bytes(
        connection,
        n_bytes=nbytes,
    )

    return message
