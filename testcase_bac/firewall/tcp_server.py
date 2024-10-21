import socket
import threading

def start_tcp_server(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind(('', port))
        server_socket.listen()
        print(f"TCP server listening on port {port}")
        while True:
            conn, addr = server_socket.accept()
            with conn:
                print(f"Connected by {addr} on port {port}")
                while True:
                    data = conn.recv(1024)
                    if not data:
                        break
                    print(f"Received data on port {port}: {data.decode('utf-8')}")
                    conn.sendall(f"Echo from port {port}: {data.decode('utf-8')}".encode('utf-8'))

ports = [80, 443, 389]

threads = []
for port in ports:
    thread = threading.Thread(target=start_tcp_server, args=(port,))
    thread.start()
    threads.append(thread)

for thread in threads:
    thread.join()
