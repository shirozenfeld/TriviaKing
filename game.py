import struct
import time
import threading
import random
from queue import Queue
from faker import Faker
import socket
import server

"""
This module contains functions related to running a trivia game server-side.

It includes functions for selecting trivia questions, running the trivia game,
and managing statistics related to the game.

"""

Bold = "\033[1m"
Red = "\033[31;1m"
Green = "\033[32;1m"
Yellow = "\033[33;1m"
Blue = "\033[34;1m"
end = "\033[0;1m"

def pick_a_question():
    """
    Randomly selects a trivia question about sloths from a predefined list.

    Returns:
    - question (str): The trivia question about sloths.
    - is_true (bool): A boolean indicating whether the statement is true or false.

    """
    try:
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
        return list(trivia_questions[0].values())[0], list(trivia_questions[0].values())[1]

    except Exception as e:
        print("Failed shuffeling a question from the bank")


def trivia_game(client_sockets):
    """
        Manages the trivia game session with connected clients.

        This function sends trivia questions to connected clients,
        collects their answers, determines the winner, and handles game flow.

        Args:
        - client_sockets (dict): A dictionary containing client sockets.

        Returns:
        - winner_name (str): The name of the winning player.

    """
    try:
        question, is_true = pick_a_question()
        # create welcome message & question
        message = f"{Yellow}Welcome to the SlothsWorld server, where we are answering trivia questions about Sloths."
        i = 1
        round = 1
        for player_name in client_sockets.keys():
            message += f"\n {Yellow}Player {i}: {player_name}"
            i += 1
        message += f"{Yellow}\n==\nTrue or false: {question}"
        while True:
            no_answer = 0
            typed_characters = []
            answers = Queue()
            dropouts = Queue()
            winner_flag = False
            clients_threads = []
            # send message and wait for answers to the questions
            print(message)
            if len(client_sockets) == 0:
                break
            for player_name, socket in client_sockets.items():
                thread = threading.Thread(target=server.handle_client, args=(player_name, socket, message, True, answers, dropouts))
                thread.start()
                clients_threads.append(thread)
            for thread in clients_threads:
                thread.join()
            # input validation is done in handle_client function
            clients_threads.clear()
            while not dropouts.empty():
                quitting_player = dropouts.get()
                del client_sockets[quitting_player]

            if len(client_sockets) == 1:
                message = f"{Red}You have been abandoned by your friends, please try connecting to a new game with new friends"
                print(message)
                thread = threading.Thread(target=server.handle_client, args=(list(client_sockets.keys())[0], list(client_sockets.values())[0], message, False, None, None))
                thread.start()
                thread.join()
                return
            j = 0
            while not answers.empty():
                j += 1
                # fold out the player-answer tuples by FIFO order
                player_name, answer = answers.get()
                typed_characters.append(answer)
                if (is_true == True and (answer == 'Y' or answer == 'T' or answer == "1")) or (
                        is_true == False and (answer == 'N' or answer == 'F' or answer == "0")):
                    # There is a winner for this round!
                    winner_flag = True
                    winner_name = player_name
                    message = f"{Green}{winner_name} is correct! The answer is {is_true}. {winner_name} wins!"
                    # Send message 1
                    print(message)
                    for player_name, socket in client_sockets.items():
                        thread = threading.Thread(target=server.handle_client, args=(player_name, socket, message, False, None, None))
                        thread.start()
                        clients_threads.append(thread)
                    for thread in clients_threads:
                        thread.join()
                    clients_threads.clear()
                    add_to_stats(len(client_sockets), winner_flag, question, typed_characters)
                    message = f"{Yellow}Game over!\nContratulations to the winner: {winner_name}"
                    message += f"{Yellow}\n=======================================\n"
                    message += read_stats()
                    print(message)
                    # Send message 2
                    for player_name, socket in client_sockets.items():
                        thread = threading.Thread(target=server.handle_client, args=(player_name, socket, message, False, None, None))
                        thread.start()
                        clients_threads.append(thread)
                    for thread in clients_threads:
                        thread.join()
                    break
                # means client didn't answer within 10 seconds
                if answer == "e":
                    no_answer += 1
                    if no_answer == len(client_sockets):
                        winner_flag = False
                        j = 0
                        break
            # If nobody answers correctly, or answered at all, another round begins
            if not winner_flag and len(client_sockets) != 0:
                message = ""
                if j == 0: #nobody answered at all
                    message += f"{Red}Nobody answered within 10 seconds. Another round begins."
                else:
                    message += f"{Red}None of the players answered correctly, try again."
                round += 1
                question, is_true = pick_a_question()
                message += f"\n{Yellow}Round {round}, played by "
                for player_name in client_sockets.keys():
                    message += f"{Yellow}{player_name}, "
                message=message[:-2]
                message += f"{Yellow}:\nTrue or false: " + question
            # there is a winner, end game
            else:
                for client_socket in client_sockets.values():
                    client_socket.close()
                return player_name
    except Exception as e:
        print(f"{Red}Failed running the trivia game: {e}")


def add_to_stats(number_of_players, winner_flag, question, typed_characters):
    """
        Records game statistics in a text file.

        Args:
        - number_of_players (int): The number of players in the game.
        - winner_flag (bool): A flag indicating whether there is a winner.
        - question (str): The trivia question.
        - typed_characters (list): A list of characters typed by players as answers.

    """
    with open("stats.txt", "a") as file:
        file.write(f"question that was asked:{question}" + '\n')
        if not winner_flag:
            file.write(f"a question nobody managed to answer:{question}" + '\n')
        file.write(f"number of players:{number_of_players}" + '\n')
        for chracter in typed_characters:
            file.write(f"{chracter}" + '\n')


def read_stats():
    """
        Reads game statistics from a text file and generates a summary.

        Returns:
        - message (str): A summary of game statistics.

    """
    try:
        questions_that_were_asked = {}
        questions_that_nobody_succeeded_answering = {}
        number_of_players = {}
        typed_answers={'F': 0, 'N': 0, '0': 0, 'T': 0, 'Y': 0, '1': 0}
        message = ""
        with open("stats.txt", "r") as file:
            for line in file:
                line = line.rstrip()
                double_points = line.find(":")
                if "question that was asked" in line:
                    question = line[double_points:]
                    questions_that_were_asked.setdefault(question, 0)
                    questions_that_were_asked[question] += 1
                if "a question nobody managed to answer" in line:
                    question = line[double_points:]
                    questions_that_nobody_succeeded_answering.setdefault(question, 0)
                    questions_that_nobody_succeeded_answering[question] += 1
                if "number of players" in line:
                    number = line[double_points:]
                    number_of_players.setdefault(number, 0)
                    number_of_players[number] += 1
                if line in typed_answers.keys():
                    typed_answers[line]+=1
        if len(questions_that_were_asked)>0 and len(number_of_players)>0 and len(typed_answers)>0: #at least one game occured
            sorted_questions = sorted(questions_that_were_asked.items(), key=lambda question: question[1], reverse=True)
            sorted_number_of_players = sorted(number_of_players.items(), key=lambda question: question[1], reverse=True)
            sorted_questions_that_nobody_succeeded_answering = {}
            if len(questions_that_nobody_succeeded_answering) > 0:
                sorted_questions_that_nobody_succeeded_answering = sorted(
                    questions_that_nobody_succeeded_answering.items(),
                    key=lambda question: question[1], reverse=True)
            categories = [sorted_questions, sorted_questions_that_nobody_succeeded_answering, sorted_number_of_players]
            categories_headlines = [
                "\n\tThe most common questions in the game's history are:",
                "\n\tThe hardest questions in the game's history are:",
                "\n\tThe most popular amounts of players in the game's history are:",
                "\n\tThe most popular character used for 'True' is: ",
                "\n\tThe most popular character used for 'False' is: ",
            ]
            message = "Statistics Table:"
            for i in range(5):
                if i == 1 and len(questions_that_nobody_succeeded_answering) == 0:
                    continue
                if i == 3:
                    message+= categories_headlines[3]
                    subset_dict = {key: value for key, value in typed_answers.items() if key in {'Y', 'T', '1'}}
                    message += f" {max(subset_dict, key=subset_dict.get)}"
                    continue
                if i == 4:
                    message += categories_headlines[4]
                    subset_dict = {key: value for key, value in typed_answers.items() if key in {'N', 'F', '0'}}
                    message += f" {max(subset_dict, key=subset_dict.get)}"
                    continue
                j = 1
                max_question = max(categories[i], key=lambda x: x[1])[1]
                message += categories_headlines[i]
                for key, value in categories[i]:
                    if value == max_question:
                        message += f"\n\t\t#{j} {key}"
                        j += 1
        return message

    except FileNotFoundError:
        print(f"{Red}The file 'stats.txt' does not exist.")
    except Exception as e:
        print(f"{Red}Failed reading statistics: {e}")
