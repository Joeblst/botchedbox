from gvm.connections import TLSConnection
from gvm.protocols.gmp import Gmp

def connect_to_gvm():
    connection = TLSConnection(hostname='127.0.0.1', port=443)
    with Gmp(connection) as gmp:
        gmp.authenticate('admin', 'admin')
        version = gmp.get_version()
        print(f'Connected to GVM. Version: {version}')

if __name__ == "__main__":
    connect_to_gvm()