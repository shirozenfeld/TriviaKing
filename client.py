# CLIENT
import socket
import struct
import sys
from faker import Faker
import re
import threading
import traceback
import keyboard
from pynput import keyboard


Bold = "\033[1m"
Red = "\033[31;1m"
Green = "\033[32;1m"
Yellow = "\033[33;1m"
Blue = "\033[34;1m"
end = "\033[0;1m"

"""
Client Script for a Multiplayer Trivia Game

This script implements the client side functionality for a multiplayer trivia game. 
It allows clients to connect to a server, receive broadcast messages, join the game, 
answer trivia questions, and receive game updates.

The client script performs the following tasks:
1. Listens for UDP broadcast messages from the server to discover available game servers.
2. Connects to the server using TCP after receiving a broadcast message.
3. Sends the player's name to the server upon connection.
4. Handles communication with the server, including sending and receiving messages.
5. Displays trivia questions received from the server and prompts the player for answers.
6. Notifies the server of the player's answer and receives game updates.
7. Handles disconnection from the server gracefully.

The script utilizes threading to concurrently handle sending and receiving messages,
providing a seamless multiplayer experience.

Author: Shir Mordechai Rozenfeld & Netta Meiri
"""


def receive_udp_offer(udp_socket):
    """
        Receive UDP offer messages from the server.

        Parameters:
        - udp_socket (socket): The UDP socket used for receiving messages.

        Returns:
        - The server's offer details.

        Note:
        - This function blocks until a valid offer message is received or an exception occurs.
        """
    while True:
        try:
            data, server_address = udp_socket.recvfrom(1024)
            magic_cookie = data[:4]
            message_type = data[4]
            if magic_cookie == b'\xab\xcd\xdc\xba' and message_type == 0x02:
                server_name_end = data.find(b'\x00', 5)
                server_name = data[5:server_name_end].decode('utf-8').strip()
                # Extract server port bytes
                server_tcp_port = data[37: 39]
                # Unpack the bytes to get the server TCP port number
                server_tcp_port_number = struct.unpack('!H', server_tcp_port)[0]
                # Extract message
                server_message_start = data.find(b'Received')
                message = data[server_message_start:].decode('utf-8')
                # Define a regular expression pattern to find the IP address after 'address'
                pattern = r'address (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
                # Find all matches of the pattern in the text
                server_ip_address = re.search(pattern, message).group(1)
                return magic_cookie, message_type, server_name, server_ip_address, server_tcp_port_number, message
        except Exception as e:
            print("receive_udp_offer:", e)
            break


def receive_tcp_messages(client_socket):
    """
       Receive messages from the server over a TCP connection.

       Parameters:
       - client_socket (socket): The client's TCP socket for receiving messages.

       Note:
       - This function continuously receives messages.
       - If the received message contains specific keywords like "true or false" or "invalid input",
         it sends a message back to the server using the `send_tcp_messages` function.
       - If the received message contains "game over" or "abandoned", it prints a message
         indicating that the server has disconnected.
       - If a `ConnectionResetError` occurs, it prints a message indicating the loss of connection.
   """
    try:
        while True:
            # Wait for incoming message
            data = client_socket.recv(1024).decode()
            if not data:
                break
            print(data)
            # Call send_tcp_messages so the client will enter input
            if "true or false" in data.lower() or "invalid input" in data.lower():
                send_tcp_messages(client_socket)
            # Check if the received data contains "game over" or "abandoned" to finish this round
            if "game over" in data.lower() or "abandoned" in data.lower():
                print("Server disconnected, listening for offer requests...")
                break

    except ConnectionResetError as e:
        print(f'{Red}Connection with the server was lost, please wait for a new connection..')

    except Exception as e:
        print("receive_tcp_messages:", type(e))
        pass


def send_tcp_messages(client_socket):
    """
        Send messages to the server over a TCP connection.

        Parameters:
        - client_socket (socket): The client's TCP socket for sending messages.

        Note:
        - This function waits for user input using keyboard events with a timeout of 10 seconds.
        - If no input is received within the timeout period, it sends a predefined message "e" (empty) to the server
          indicating that the client's response time has exceeded the limit.
        - If a `ConnectionResetError` occurs during the sending process, it returns without performing any action.
    """
    with keyboard.Events() as events:
        # Wait maximum 10 seconds for input
        event = events.get(10)
        # Client didn't enter input, send "e" (empty) to the server
        if event is None:
            ans = "e"
            try:
                client_socket.sendall(ans.encode())
            except ConnectionResetError as e:
                return
            print(f"{Red}Time's Up! You have exceeded the 10 seconds window for answering")
            return
        # Client entered input, send it to the server
        else:
            input = sys.stdin.readline().strip()
            client_socket.sendall(input.encode())


def main():
    """
        Main function to start the client-side application.

        This function performs the following steps:
        1. Generates a random player name using the Faker library.
        2. Creates a UDP socket to listen for offer messages.
        3. Binds the UDP socket to a specific port and listens for incoming offer messages.
        4. Upon receiving an offer message, extracts necessary information (server IP, port, etc.) and connects to the server via TCP.
        5. Sends the player name to the server over the TCP connection.
        6. Starts a thread to handle receiving messages from the server.
        7. Joins the receiving thread to wait for it to finish before closing the client socket.

        Note:
        - This function continuously runs in a loop to listen for offer messages and connect to the server.
        - If any exception occurs during the execution, the function terminates the program.
    """
    # Pick a random player name
    fake = Faker()
    player_name = fake.name()
    print(f'Your name is {player_name}')
    server_udp_port = 13117
    try:
        while True:
            # Create a UDP socket
            udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            udp_socket.bind(("", server_udp_port))
            print(f"{Blue}Client started, listening for offer requests...")
            # Listen for offer messages
            magic_cookie, message_type, server_name, server_ip_address, server_tcp_port, message = receive_udp_offer(
                udp_socket)
            print(message)
            udp_socket.close()
            # Connect to the server via TCP
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                client_socket.connect((server_ip_address, server_tcp_port))
            except Exception as e:
                print(e)
            print("Connected to the server.")
            # Send the player name
            client_socket.sendall(player_name.encode() + b'\n')
            # Start threads for sending and receiving messages
            receive_thread = threading.Thread(target=receive_tcp_messages(client_socket))
            receive_thread.start()
            receive_thread.join()
            client_socket.close()
    except Exception as e:
        sys.exit()


if __name__ == "__main__":
    main()
