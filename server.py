import queue
import socket
import struct
import time
import threading
import random
from queue import Queue


def pick_a_question():
    # List of trivia questions about sloths
    trivia_questions = [
        {"question": "Sloths are mammals.", "is_true": True},
        {"question": "Sloths spend most of their time sleeping.", "is_true": True},
        {"question": "Sloths are fast runners.", "is_true": False},
        {"question": "Sloths have a very slow metabolism.", "is_true": True},
        {"question": "Sloths are excellent swimmers.", "is_true": False},
        {"question": "Sloths only eat leaves.", "is_true": True},
        {"question": "Sloths are closely related to monkeys.", "is_true": False},
        {"question": "Sloths have a large appetite.", "is_true": False},
        {"question": "Sloths are nocturnal animals.", "is_true": False},
        {"question": "Sloths have a strong sense of smell.", "is_true": True},
        {"question": "Sloths have long tongues.", "is_true": True},
        {"question": "Sloths have good eyesight.", "is_true": False},
        {"question": "Sloths have a body temperature similar to humans.", "is_true": True},
        {"question": "Sloths are found only in Africa.", "is_true": False},
        {"question": "Sloths have a natural predator in the wild.", "is_true": False},
        {"question": "Sloths communicate using loud vocalizations.", "is_true": False},
        {"question": "Sloths can live up to 40 years in the wild.", "is_true": True},
        {"question": "Sloths have a strong grip and can hang upside down for hours.", "is_true": True},
        {"question": "Sloths have multiple stomach chambers to digest their food.", "is_true": False},
        {"question": "Sloths are active hunters.", "is_true": False}
    ]
    # Shuffle the list of trivia questions
    random.shuffle(trivia_questions)
    # Print the trivia questions
    return trivia_questions[0]

def get_local_ip_address():
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
        print("Error:", e)
        return None

# getting available port number from operating system
def get_free_port():
    # Create a socket object
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # Bind the socket to a port (0 means let the OS choose a free port)
        s.bind(("", 0))
        # Get the assigned port number
        port = s.getsockname()[1]
    except Exception as e:
        print("Error:", e)
        port = None
    finally:
        # Close the socket
        s.close()
    return port

def send_udp_broadcast_message(server_ip_address, server_broadcast_port, server_tcp_port_number, stop_event):
    broadcast_ip = "255.255.255.255"
    server_name = "Misty"
    #set UDP socket properties
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    #set socket options to allow broadcast
    udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    #send broadcast message
    try:
        print(f"Server started, listening on IP address {server_ip_address}")
        while not stop_event.is_set():
            # Construct message
            message = f"Received offer from server “{server_name}” at address {server_ip_address}, attempting to connect..."
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
        print(e)
        print("Stopping UDP broadcast")
        udp_socket.close()

def run_udp_and_tcp_connections(server_ip_address, server_tcp_listening_port,server_udp_broadcast_port):
    stop_event = threading.Event()  # Event to stop the UDP broadcast thread and TCP listening socket
    try:
        # Create server TCP socket
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((server_ip_address, server_tcp_listening_port))
        server_socket.listen(3)
        # Create server UDP socket & Start broadcasting offer messages in a separate thread
        offer_thread = threading.Thread(target=send_udp_broadcast_message(server_ip_address, server_udp_broadcast_port, server_tcp_listening_port, stop_event)).start()

        # Dictionary to store client sockets
        client_sockets = {}

        # Set a timer to stop sending UDP offers and break the loop after 10 seconds without action
        try:
            # Accept client connections
            while not stop_event.is_set():
                start_time=time.time()
                client_socket, addr = server_socket.accept()
                end_time=time.time()
                if (end_time-start_time)>10:
                    stop_event.set() # Stop sending UDP offers
                    offer_thread.join()
                    server_socket.close()
                    return client_sockets
                player_name = client_socket.recv(1024).decode().strip() # Receive player name from the client
                client_sockets[player_name] = client_socket # Add the client socket to the list
                # Stop accepting clients if you have already reached 3
                # if len(client_socket) == 3:
                #     stop_event.set()
                #     offer_thread.join()
                #     server_socket.close()
                #     return client_sockets
                # Cancel the previous timer if it's still running, and restart it

        except Exception as e:
            stop_event.set()
            for client_socket in client_sockets.values():
                client_socket.close()
            server_socket.close()

    except Exception as e:
        print(f"Error trying to set a TCP server: {e}")
        for client_socket in client_sockets.values():
            client_socket.close()
        server_socket.close()

#Function to handle communication with each client
def handle_client(player_name, client_socket, message, should_wait_for_answer, data_structure):
    if not should_wait_for_answer:
        client_socket.sendall(message.encode())
    else:
        valid_answers = ["Y", "T", "1", "N", "F", "0"]
        client_socket.sendall(message.encode())
        while True:
            # Receive data from the client
            data = client_socket.recv(1024)
            if not data or len(data) > 1 or data.decode() not in valid_answers:
                error_message = "Invalid input, please answer again, Y/T/1 for 'True' or N/F/0 for 'False'"
                client_socket.sendall(error_message.encode())  # Encode error message before sending
            else:
                data_structure.put(player_name, data.decode())
                break

def trivia_game(client_sockets):
    answers=Queue()
    question,is_true=trivia_game()
    # create welcome message & question
    message="Welcome to the Mystic server, where we are answering trivia questions about Sloths."
    i=1
    round=1
    for player_name in client_sockets.keys():
        message+=f"\n Player {i}: {player_name}"
        i+=1
    message+="\nTrue or false: "+question
    while True:
        clients_threads = []
        # send messages and wait for answers to the questions
        for player_name,socket in client_sockets:
            thread=threading.Thread(target=handle_client, args=(player_name,socket,question,True,answers)).start()
            clients_threads.append(thread)
        for thread in clients_threads:
            thread.join()
            # input validation is done in handle_client function
        clients_threads.clear()
        winner_flag = False
        for i in range(len(answers)):
            # fold out the player-answer tuples by FIFO order
            player_name, answer=answers.get()
            if ((is_true) and (answer=='Y' or answer=='T' or answer=="1")) or ((not is_true) and (answer=='N' or answer=='F' or answer=="0")):
                # There is a winner for this round!
                winner_flag=True
                winner_name=player_name
                message=f"{winner_name} is correct! {winner_name} wins!"
                # Send message 1
                for player_name, socket in client_sockets:
                    thread = threading.Thread(target=handle_client, args=(player_name, socket, message,False,None)).start()
                    clients_threads.append(thread)
                for thread in clients_threads:
                    thread.join()
                clients_threads.clear()
                add_to_stats(winner_name)
                message = f"Game over!\nContratulations to the winner: {winner_name}"
                message += "\n=======================================\n"
                message += read_stats()
                # Send message 2
                for player_name, socket in client_sockets:
                    thread = threading.Thread(target=handle_client(),
                                              args=(player_name, socket, message, False, None)).start()
                    clients_threads.append(thread)
                for thread in clients_threads:
                    thread.join()
                break
        # If nobody answers correctly, another round begins
        if not winner_flag:
            round+=1
            question, is_true = trivia_game()
            message=f"Round {round}, played by "
            for player_name in client_sockets.keys():
                message+=f"{player_name}, "
            message+=":\nTrue or false: "+question
    #there is a winner, end game
    for client_socket in client_sockets.values():
        client_socket.close()
    return player_name

def add_to_stats(player_name):
    with open("stats.txt", "w") as file:
        file.writelines(player_name)
def read_stats():
    try:
        with open("stats.txt","r") as file:
            lines= {}
            for line in file:
                line=line.rstrip()
                lines[line]= lines[line] = lines.get(line, 0) + 1
            sorted_winners=sorted(lines.items(),key=lambda player:player[1],reverse=True)
            message="Winners List Statistical Table:"
            i=1
            for player,wins in sorted_winners:
                message+=f"\nnumber #{i}: {player}"
                i+=1
            return message
    except FileNotFoundError:
        print("The file 'stats.txt' does not exist.")
    except Exception as e:
        print(f"An error occurred: {e}")

def main():
    while True:
        server_ip_address = get_local_ip_address()
        server_udp_broadcast_port = 13117
        server_tcp_listening_port = get_free_port()
        client_sockets=run_udp_and_tcp_connections(server_ip_address,server_tcp_listening_port,server_udp_broadcast_port)
        if len(client_sockets)>1 and len(client_sockets)<4:
            trivia_game(client_sockets)

if __name__ == "__main__":
    main()


