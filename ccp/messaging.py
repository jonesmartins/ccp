import pickle
import socket
from typing import Dict


def send_message(connection: socket.socket, message: Dict):
    """
    Envia mensagem pela conexão para recv_message.
    :param connection: Conexão TCP
    :param message: Mensagem (pedido)
    """
    request_bytes = pickle.dumps(message)
    connection.sendall(request_bytes)
    print('Sent all request_bytes.')


def recv_message(connection: socket.socket, bufsize=1024) -> Dict:
    """
    Recebe mensagem pela conexão enviada por send_message.
    :param connection: Conexão TCP
    :param bufsize: Tamanho do buffer de recebimento
    :return: Mensagem
    """
    message_bytes = b''
    while (recv_bytes := connection.recv(bufsize)):
        print('Received bytes:', recv_bytes)
        message_bytes += recv_bytes

    message = pickle.loads(message_bytes)
    return message
