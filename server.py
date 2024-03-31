import socket
import time
import threading

def send_udp_broadcast_message():
    server_ip_address = "127.0.0.1"
    #todo: לשנות את הפורט כך שיהיה שיתופי
    clients_udp_ports=5005 #the port from which the broadcast message will be sent
    server_udp_port=clients_udp_ports
    #todo: לעשות אנקודינג להודעה
    message="Received offer from server “Mystic” at address "+server_ip_address+", attempting to connect..."

    #set UDP socket properties
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # udp socket over internet
    udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    #send broadcast message
    try:
        while True:
            udp_socket.sendto(message, ("255.255.255.255", clients_udp_ports))
    except KeyboardInterrupt:
        print("Stopping UDP broadcast")
        udp_socket.close()

def main():
    thread=threading.Thread(target=send_udp_broadcast_message)
    server_tcp_socket=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_tcp_socket.bind('127.0.0.1')
    server_tcp_socket.listen(5)
    server_tcp_port=1000
    print("Server is listening on port ", server_tcp_port)
    while True:
        client,address=server_tcp_socket.accept()
        print(f"Connection with {address} has been established!")
        client.send("Welcome to the server!") #todo: להוסיף פה אנקודינג
        client.close()


if __name__=="__main__":
    main()


