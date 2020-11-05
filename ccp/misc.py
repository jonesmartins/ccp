import socket

import requests


def buscar_endereco_lan():
    """
    Busca endereço para conexão LAN.
    OBS:
        Não precisa de internet.
    :return: IPv4 local (ex.: 192.168.0.1)
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.connect(('<broadcast>', 0))
    local_address, _ = s.getsockname()
    s.close()
    return local_address


def buscar_enderecos_globais():
    """
    Busca endereço global IPv4 e IPv6.
    OBS.:
        Precisa de internet.
    :return: IPv4 e IPv6 globais.
    """
    ipv4_response = requests.get('https://api.ipify.org/?format=json')
    ipv4_response_json = ipv4_response.json()
    ipv4 = ipv4_response_json['ip']

    ipv6_response = requests.get('https://jsonip.com')
    ipv6_response_json = ipv6_response.json()
    ipv6 = ipv6_response_json['ip']

    return ipv4, ipv6
