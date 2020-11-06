# import pytest

# def test_parse_address():
#     pass


# def test_is_valid_ipv4_address():
#     pass

# def test_is_valid_ipv6_address():
#     assertEquals(validate_ip('0.0.0.0'), '0.0.0.0')
#     assertEquals(validate_ip('255.255.255.255'), '255.255.255.255')
#     assertEquals(validate_ip('127.0.0.1'), '127.0.0.1')
#     assertRaises(ValueError, validate_ip, '127.1')
#     assertRaises(ValueError, validate_ip, '255.')
#     assertRaises(ValueError, validate_ip, '')
#     assertEquals(validate_ip('localhost'), 'localhost')

# def test_validate_port():
#     assertRaises(ValueError, validate_port, -1)
#     assertEqual(validate_port(0), 0)
#     assertEqual(validate_port(2**16 - 1), 2**16 - 1)
#     assertRaises(ValueError, validate_port, 2**16)
#     assertRaises(ValueError, validate_port, '10')


# def test_validate_path():
#     # Inicia diretório de testes.
#     if not os.path.exists('tmp'):
#         os.mkdir('tmp')
#
#     os.chdir('tmp')
#     if not os.path.exists('directory'):
#         os.mkdir('directory')
#
#     open('directory/file', 'w').close()
#
#     # TESTES (Em tmp)
#     try:
#         path = ''  # Diretório atual
#         abs_path = get_abspath(path)
#         print(f'Abs of "{path}": "{abs_path}"')
#         with pytest.raises(FileExistsError):
#             validate_path(abs_path)
#
#         path = '.'  # Diretório atual
#         abs_path = get_abspath(path)
#         print(f'Abs of "{path}": "{abs_path}"')
#         with pytest.raises(FileExistsError):
#             validate_path(abs_path)
#
#         path = '..'  # Diretório superior
#         abs_path = get_abspath(path)
#         print(f'Abs of "{path}": "{abs_path}"')
#         with pytest.raises(FileExistsError):
#             validate_path(abs_path)
#
#         path = '/directory'  # Funciona (assim como "/home")
#         abs_path = get_abspath(path)
#         print(f'Abs of "{path}": "{abs_path}"')
#         assert validate_path(abs_path) == abs_path
#
#         path = 'directory/'  # Diretório inferior (nome válido)
#         abs_path = get_abspath(path)
#         print(f'Abs of "{path}": "{abs_path}"')
#         with pytest.raises(FileExistsError):
#             validate_path(abs_path)
#
#         path = 'directory'  # Diretório inferior (nome válido)
#         abs_path = get_abspath(path)
#         print(f'Abs of "{path}": "{abs_path}"')
#         with pytest.raises(FileExistsError):
#             validate_path(abs_path)
#
#         path = '../directory'  # Não existe.
#         abs_path = get_abspath(path)
#         print(f'Abs of "{path}": "{abs_path}"')
#         with pytest.raises(FileNotFoundError):
#             validate_path(abs_path)
#
#         path = '/file'  # Funciona (assim como "/home")
#         abs_path = get_abspath(path)
#         print(f'Abs of "{path}": "{abs_path}"')
#         assert validate_path(abs_path) == abs_path
#
#         path = 'file/'  # Arquivo no diretório atual (nome inválido)
#         abs_path = get_abspath(path)
#         print(f'Abs of "{path}": "{abs_path}"')
#         with pytest.raises(IsADirectoryError):
#             validate_path(abs_path)
#
#         path = 'file'  # Arquivo no diretório atual (nome válido)
#         abs_path = get_abspath(path)
#         assert validate_path(abs_path) == abs_path
#
#     finally:
#         # Apaga diretório e volta às condições anteriores.
#         os.chdir('..')
#         shutil.rmtree('tmp')


import messaging
import threading
import socket

def test_send_recv():
    ADDRESS = ('localhost', 12345)



    def sending_side():
        print('Sending side.')
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(ADDRESS)
            s.listen(1)
            print('Server waiting for client connection')

        except Exception as exc:
            print('Sending side error:', exc)
        else:
            connection, _ = s.accept()
            print('Server accepted connection with client')
            try:
                first_message = 'Hello!'
                print('Server sending first message.')
                messaging.send_message(connection, first_message)
                print('Server sent first message.')

                print('Server receiving last message.')
                last_message = messaging.recv_message(connection)
                print('Server received last message.')
                assert last_message == 'Goodbye!'
            finally:
                # connection.shutdown(socket.SHUT_RDWR)
                connection.close()
                print('Closed connection to client.')
        finally:
            s.close()
            print('Closed server.')

    def receiving_side():
        print('Receiving side.')
        connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connection.settimeout(3)
        try:
            print('Client connecting to server.')
            connection.connect(ADDRESS)
            connection.settimeout(None)
            print('Client connected to the server.')
        except Exception as exc:
            print('Receiving side error:', exc)
        else:

            first_message = messaging.recv_message(connection)
            assert first_message == 'Hello!'

            last_message = 'Goodbye!'
            print('Client sending last message')
            messaging.send_message(connection, last_message)
            print('Client sent last message')

        finally:
            # connection.shutdown(socket.SHUT_RDWR)
            connection.close()
            print('Closed connection to server.')

    thread1 = threading.Thread(
        target=sending_side,
        args=()
    )

    thread2 = threading.Thread(
        target=receiving_side,
        args=()
    )

    print('Creating sending and receiving threads.')
    thread1.start()
    import time
    time.sleep(1)
    thread2.start()

    thread1.join()
    thread2.join()


if __name__ == '__main__':
    test_send_recv()
    # pytest.main()
