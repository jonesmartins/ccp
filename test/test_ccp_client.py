import pytest

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





if __name__ == '__main__':
    pytest.main()
