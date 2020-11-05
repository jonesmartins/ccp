import argparse


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
        default=False,
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


def get_server_parser():
    """
    Leitor de argumentos da aplicação servidor.
     - max_streams: Quantidade máxima de conexões paralelas por pedido.
     - debug_mode: Ativa mensagens de depuração.

    :return: Leitor de argumentos.
    """
    parser = argparse.ArgumentParser(
        prog='CCPD',
        description='Envio de arquivos comprimidos em paralelo'
    )

    default_port = 4567
    parser.add_argument(
        '-p', '--port',
        type=int,
        nargs='?',
        default=default_port,
        dest='port',
        help=f'A porta do servidor (padrão: {default_port})'
    )

    parser.add_argument(
        '-d', '--debug-mode',
        action='store_true',
        dest='debug_mode',
        help='Ativa mensagens de depuração'
    )

    return parser
