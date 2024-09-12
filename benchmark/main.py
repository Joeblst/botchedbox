from gvm.connections import UnixSocketConnection
from gvm.protocols.gmp import Gmp

def connect_to_gvm():
    connection = UnixSocketConnection(path='/var/run/gvmd.sock')
    with Gmp(connection) as gmp:
        version = gmp.get_version()
        print(f'Connected to GVM. Version: {version}')

if __name__ == "__main__":
    connect_to_gvm()