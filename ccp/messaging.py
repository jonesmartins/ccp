import pickle
import socket


def send_message(connection: socket.socket, message, nbytes: int = 512):
    """
    Envia mensagem  de <n_bytes> (padrão: 512B) pela conexão para recv_message.
    :param connection: Conexão TCP
    :param message: Mensagem
    :param nbytes: Tamanho fixo da mensagem. Deve ser concordado entre ambos.
    """
    message_sendbuf = bytearray(nbytes)
    request_bytes = pickle.dumps(message)
    message_sendbuf[:len(request_bytes)] = request_bytes
    connection.sendall(message_sendbuf)


def recv_n_bytes(
        connection: socket.socket,
        n_bytes: int,
        bufsize=1024
):
    """
    Recebe uma quantidade fixa de bytes.
    :param connection: Conexão TCP
    :param n_bytes: Tamanho da mensagem
    :param bufsize: Tamanho do buffer de recebimento
    :return: Mensagem desserializada
    """
    empty_byte = b''
    message_bytes = b''
    total_bytes_received = 0
    while total_bytes_received < n_bytes:
        recv_bytes = connection.recv(min(n_bytes - total_bytes_received, bufsize))
        if recv_bytes == empty_byte:
            raise RuntimeError('Broken connection.')
        message_bytes += recv_bytes
        total_bytes_received += len(recv_bytes)

    return message_bytes


def recv_message(connection: socket.socket, nbytes=512):
    """
    Recebe mensagem pela conexão enviada por send_message.
    :param connection: Conexão TCP
    :param nbytes: Tamanho esperado da mensagem
    :return: Mensagem
    """

    message_bytes = recv_n_bytes(
        connection,
        n_bytes=nbytes,
    )

    message = pickle.loads(message_bytes)
    return message
