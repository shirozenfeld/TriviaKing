# todo: לשנות את הפורט כך שיהיה שיתופי

import socket
import sys
import threading


def receive_udp_offer(udp_socket):
    while True:
        try:
            data, server_address = udp_socket.recvfrom(1024)
            magic_cookie = data[:4]
            message_type = data[4]
            if magic_cookie == b'\xab\xcd\xdc\xba' and message_type == 0x02:
                server_name = data[5:37].decode().strip()
                server_ip_address = '.'.join(map(str, data[37:41]))

                # Extract server port bytes
                if len(data) < 43:
                    raise ValueError("Invalid UDP packet: Packet length is too short")
                server_tcp_port = int.from_bytes(data[41:43], byteorder='big')

                # Extract message
                message = data[43:].decode()

                return magic_cookie, message_type, server_name, server_ip_address, server_tcp_port, message
        except Exception as e:
            print("Error:", e)
            break


def receive_tcp_messages(client_socket,  stop_event):
    while not stop_event.is_set():
        try:
            data = client_socket.recv(1024).decode()
            if not data:
                break
            print(data)
            # Check if the received data contains "game over"
            if "game over" in data.lower():
                print("Server disconnected, listening for offer requests...")
                stop_event.is_set()
                break
        except Exception as e:
            print("Error receiving message:", e)
            break


def send_tcp_messages(client_socket,  stop_event):
    while not stop_event.is_set():
        try:
            message = input()
            client_socket.sendall(message.encode())
        except Exception as e:
            print("Error receiving message:", e)
            break


def main():
    server_udp_port = 13117
    stop_event = threading.Event()
    while True:
        try:
            # Create a UDP socket
            udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp_socket.bind(("", server_udp_port))

            print("Client started, listening for offer requests...")

            # Listen for offer messages
            magic_cookie, message_type, server_name, server_ip_address, server_tcp_port, message = receive_udp_offer(udp_socket)
            print(message)

            # Connect to the server via TCP
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((server_ip_address, server_tcp_port))
            print("Connected to the server.")

            # Send player name to the server
            player_name = input("Enter your name: ")
            client_socket.sendall(player_name.encode() + b'\n')

            # Start threads for sending and receiving messages
            receive_thread = threading.Thread(target=receive_tcp_messages, args=(client_socket, stop_event)).start()
            send_thread = threading.Thread(target=send_tcp_messages, args=(client_socket, stop_event)).start()

            receive_thread.join()
            send_thread.join()
            client_socket.close()
        except Exception as e:
            print("Error receiving message:", e)
            sys.exit()


if __name__ == "__main__":
    main()




