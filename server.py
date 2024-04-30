import struct
import time
import threading
import random
from queue import Queue
from faker import Faker
import socket
import game

Bold = "\033[1m"
Red = "\033[31;1m"
Green = "\033[32;1m"
Yellow = "\033[33;1m"
Blue = "\033[34;1m"
end = "\033[0;1m"

"""
Server Script for a Multiplayer Trivia Game

This script implements the server side functionality for a multiplayer trivia game. 
It allows clients to connect, receive UDP broadcast offers, join the game, answer 
trivia questions, and receive game updates.

The server script performs the following tasks:
1. Sends UDP broadcast messages to notify clients of the available game server.
2. Listens for client connections via TCP after sending broadcast messages.
3. Accepts client connections.
4. Sends trivia questions to connected clients and awaits their answers.
5. Validates and records player answers, determines winners, and updates game state.
6. Manages client connections, handles disconnections, and cleans up resources.
7. Provides statistics on game winners and maintains a winners list.

The script utilizes threading to concurrently handle UDP broadcasting, TCP connections, 
and client communication, ensuring smooth gameplay and responsiveness.

Author: Shir Mordechai Rozenfeld & Netta Meiri
"""


def get_local_ip_address():
    """
    Getting the LAN ip address of the server, to which the clients can reach out.
    Returns: the LAN ip address of the server
    """
    try:
        # Create a socket object
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Try connecting to Google Servers
        s.connect(("8.8.8.8", 80))
        # Get the local IP address connected to the remote server
        ip_address = s.getsockname()[0]
        # Close the socket
        s.close()
        return ip_address
    except Exception as e:
        print("get_local_ip_address:", e)
        return None



def get_free_port():
    """
    Getting available port number from operating system.
    Parameters: None
    Returns: a free port on which the server can use for tcp listening socket, allocated by the OS
    """
    # Create a socket object
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # Bind the socket to a port (0 means let the OS choose a free port)
        s.bind(("", 0))
        # Get the assigned port number
        port = s.getsockname()[1]
    except Exception as e:
        print("get_free_port:", e)
        port = None
    finally:
        # Close the socket
        s.close()
    return port



def send_udp_broadcast_message(server_ip_address, server_broadcast_port, server_tcp_port_number, stop_event):
    """
    Sending UDP packets on broadcast, offering end-users in the LAN to connect the server and join the game.
    Parameters:
    - server_ip_address (str): The IP address of the server in the LAN
    - server_broadcast_port (int): The port number on which the broadcast message will be sent.
    - server_tcp_port_number (int): The TCP port number of the server.
    - stop_event (threading.Event): A threading event object used to control the execution of the function.
    Returns: None
    """
    broadcast_ip = "255.255.255.255"
    server_name = "TONGUE"
    # set UDP socket properties
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # set socket options to allow broadcast
    udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    udp_socket.bind((server_ip_address, server_broadcast_port))
    # send broadcast message
    try:
        print(f"{Yellow}Server started, listening on IP address {server_ip_address}")
        while not stop_event.is_set():
            # Construct message
            message = f"Received offer from server \"{server_name}\" at address {server_ip_address}, attempting to connect..."
            # Packet format
            magic_cookie = b'\xab\xcd\xdc\xba'
            message_type = b'\x02'
            server_name_bytes = server_name.encode().ljust(32, b'\x00')
            server_port_bytes = struct.pack("!H", server_tcp_port_number)
            # Concatenate packet components
            packet = magic_cookie + message_type + server_name_bytes + server_port_bytes + message.encode()
            # Send packet
            udp_socket.sendto(packet, (broadcast_ip, server_broadcast_port))
            time.sleep(1)

    except Exception as e:
        print(f"{Red}Failed sending UDP messages in the LAN via broadcast.")
        udp_socket.close()


def run_udp_and_tcp_connections(server_ip_address, server_tcp_listening_port, server_udp_broadcast_port):
    """
    Establishes both UDP and TCP sockets in order to send offer messages and to accept clients connections, respectively.
    Parameters:
    - server_ip_address (str): The IP address of the server in the LAN.
    - server_tcp_listening_port (int): The TCP port number on which the server listens for incoming connections.
    - server_udp_broadcast_port (int): The UDP port number on which the server broadcasts offer messages.

    Returns:
    - client_sockets (dict): A dictionary containing client sockets keyed by player names.
    """
    stop_event = threading.Event()  # Event to stop the UDP broadcast thread and TCP listening socket
    try:
        # Create server TCP socket
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((server_ip_address, server_tcp_listening_port))
        server_socket.listen(5)
        # Create server UDP socket & Start broadcasting offer messages in a separate thread
        offer_thread = threading.Thread(target=send_udp_broadcast_message, args=(
            server_ip_address, server_udp_broadcast_port, server_tcp_listening_port, stop_event))
        offer_thread.start()
        # Dictionary to store client sockets
        client_sockets = {}

        # Set a timer to stop sending UDP offers and break the loop after 10 seconds without action
        try:
            # Accept client connections
            while not stop_event.is_set():
                # If there is at least one player, start counting down 10 seconds for the joining of the next one.
                if len(client_sockets) >= 1:
                    server_socket.settimeout(10)  # Set timeout for accept() to 10 seconds
                    try:
                        client_socket, addr = server_socket.accept()
                        server_socket.settimeout(None)  # Reset timeout
                    # If the next player hasn't joined in 10 seconds, stop sending UDP messages and restart the process
                    except socket.timeout:
                        stop_event.set()  # Stop sending UDP offers in order to begin the game
                        offer_thread.join()
                        server_socket.close()
                        return client_sockets
                else:
                    client_socket, addr = server_socket.accept()

                player_name = client_socket.recv(1024).decode().strip()  # Receive player name from the client`
                while True:
                    if player_name in client_sockets.keys():
                        fake = Faker()
                        player_name = fake.name()
                    else:
                        client_sockets[player_name] = client_socket  # Add the client socket to the list]
                        break

        except Exception as e:
            print(f"{Red}Failed accepting new clients.")
            stop_event.set()
            for client_socket in client_sockets.values():
                client_socket.close()
            server_socket.close()

    except Exception as e:
        print(f"Error trying to set a TCP server: {e}")
        if len(client_sockets.keys()) > 0:
            for client_socket in client_sockets.values():
                client_socket.close()
        server_socket.close()


# Function to handle communication with each client
def handle_client(player_name, client_socket, message, should_wait_for_answer, answers, dropouts):
    """
    Handles communication with a client and applies input validation.

    Parameters:
    - player_name (str): The name of the player associated with the client.
    - client_socket (socket.socket): The socket object representing the client connection.
    - message (str): The message to send to the client.
    - should_wait_for_answer (bool): Indicates whether the function should wait for an answer from the client.
    - answers (queue.Queue): A queue to store answers received from clients.
    - dropouts (queue.Queue): A queue to store player names that have disconnected and should later be erased from the data structure.

    Returns: None
    """
    try:

        if not should_wait_for_answer:
            try:
                client_socket.sendall(message.encode())
            except Exception as e:
                # Everybody left the game thus no socket is valid. Pass the exception and start a new game.
                pass
        else:
            valid_answers = ["Y", "T", "1", "N", "F", "0", "e"]
            client_socket.sendall(message.encode())
            while True:
                # Receive data from the client
                data = client_socket.recv(1024)
                if data == 0:  # connection was closed, remove the player
                    dropouts.put(player_name)
                    return
                if not data or data.decode() not in valid_answers: # Invalid answer, ask the player to change it
                    error_message = "Invalid input, please answer again, Y/T/1 for 'True' or N/F/0 for 'False'"
                    client_socket.sendall(error_message.encode())  # Encode error message before sending
                else:
                    answers.put((player_name, data.decode()))
                    break
    except ConnectionResetError as e:
        # Player has quit the game
        dropouts.put(player_name)

    except ConnectionAbortedError as e:
        message = f"{Red}No input received within 10 seconds\n"
        print(message)
        return

    except KeyboardInterrupt as e:
        print("Goodbye.")


def main():
    """
    Main function to start the server-side application.

    This function performs the following steps:
    1. Retrieves the local IP address of the server.
    2. Determines a free port for UDP broadcasting and TCP listening.
    3. Runs UDP and TCP connections to handle client interactions.
    4. If multiple clients join, starts a trivia game using the 'trivia_game' function from the 'game' module.
    5. If only one client joins, sends a message indicating no other players have joined.
    6. Handles exceptions that may occur during the execution, printing a failure message if an error occurs.

    Note:
    - This function continuously runs in a loop to manage client connections and game sessions.
    - Any exception encountered during execution is caught and results in a failure message being printed.
    """
    try:
        while True:
            server_ip_address = get_local_ip_address()
            server_udp_broadcast_port = 13117 # hard-coded, given in the instructions
            server_tcp_listening_port = get_free_port()
            client_sockets = run_udp_and_tcp_connections(server_ip_address, server_tcp_listening_port,
                                                         server_udp_broadcast_port)
            if len(client_sockets) > 1:
                game.trivia_game(client_sockets)
                print(f"{Yellow}Game over, sending out offer requests...")

            elif len(client_sockets) == 1:
                message = f"{Red}No other players have joined, please try again."
                for player_name, socket in client_sockets.items():
                    handle_client(player_name, socket, message, False, None, None)
                    socket.close()

    except Exception as e:
        print(f"{Red}Failed running the game")


if __name__ == "__main__":
    main()

