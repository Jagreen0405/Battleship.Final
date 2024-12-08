# server.py
import socket
import threading
import pickle
import random
import traceback

# Server configuration
HOST = 'localhost'
PORT = 9999
map_size = 10
ships = {"Carrier": 5, "Battleship": 4, "Cruiser": 3, "Submarine": 2, "Destroyer": 2}
ship_symbols = {"Carrier": "C", "Battleship": "B", "Cruiser": "R", "Submarine": "S", "Destroyer": "D"}

# Initialize player data
player_boards = [None, None]  # Boards for player 1 and player 2
attack_boards = [None, None]  # Boards to track hits/misses
ship_placements = [set(), set()]  # Track placed ships for each player
turn = None  # Track whose turn it is
phase = "placement"  # Game phase: "placement" or "combat"
ships_sunk = [0, 0]  # Track number of sunk ships for each player

# Set up server socket
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen(2)
print("Server started. Waiting for connections...")

clients = []

def handle_client(conn, player_id):
    """Handles communication with a single client."""
    global phase, turn

    try:
        print(f"Handling Player {player_id + 1}.")
        conn.send(pickle.dumps({"type": "start", "player_id": player_id}))

        while True:
            try:
                # Receive and decode data from client
                raw_data = conn.recv(4096)  # Increased buffer size
                if not raw_data:
                    print(f"Player {player_id + 1} disconnected.")
                    break

                message = pickle.loads(raw_data)
                print(f"Decoded message from Player {player_id + 1}: {message}")

                # Handle placement phase
                if message.get("type") == "place_ship" and phase == "placement":
                    handle_place_ship(conn, player_id, message)

                # Handle attack phase
                elif message.get("type") == "attack" and phase == "combat":
                    handle_attack(conn, player_id, message)

            except Exception as e:
                print(f"Error handling Player {player_id + 1}: {e}")
                traceback.print_exc()
                break

    finally:
        conn.close()
        print(f"Connection with Player {player_id + 1} closed.")

def handle_place_ship(conn, player_id, message):
    """Handles ship placement for a player."""
    global phase, turn

    try:
        ship_name = message.get("ship")
        coords = message.get("coords")
        orientation = message.get("orientation")

        row, col = coords
        print(f"Player {player_id + 1} is placing {ship_name} at ({row}, {col}) with orientation {orientation}.")

        # Validate placement
        if ship_name in ship_placements[player_id]:
            conn.send(pickle.dumps({"type": "error", "message": "Ship already placed."}))
            return
        if not place_ship(player_boards[player_id], row, col, ships[ship_name], orientation, ship_symbols[ship_name]):
            conn.send(pickle.dumps({"type": "error", "message": "Invalid placement."}))
            return

        # Update state and notify client
        ship_placements[player_id].add(ship_name)
        conn.send(pickle.dumps({
            "type": "ship_placed",
            "ship": ship_name,
            "coords": (row, col),
            "orientation": orientation,
            "symbol": ship_symbols[ship_name]
        }))

        # Check if this player has finished placing all ships
        if len(ship_placements[player_id]) == len(ships):
            conn.send(pickle.dumps({"type": "all_ships_placed"}))
            print(f"Player {player_id + 1} has finished placing all ships.")
            
            # Check if both players have finished placing ships
            if all(len(ship_placements[i]) == len(ships) for i in range(2)):
                phase = "combat"
                turn = random.randint(0, 1)  # Randomly select which player goes first
                print(f"All players have placed their ships. Moving to combat phase. Player {turn + 1} starts.")
                
                # Send turn notifications to both players
                for i in range(2):
                    if i == turn:
                        clients[i].send(pickle.dumps({"type": "your_turn"}))
                        print(f"Sent 'your_turn' to Player {i + 1}")
                    else:
                        clients[i].send(pickle.dumps({"type": "wait_turn"}))
                        print(f"Sent 'wait_turn' to Player {i + 1}")
            else:
                # If the other player hasn't finished, send a waiting message
                conn.send(pickle.dumps({"type": "wait_turn"}))

    except Exception as e:
        print(f"Error during ship placement for Player {player_id + 1}: {e}")
        traceback.print_exc()

def is_ship_sunk(player_id, ship_symbol):
    """Check if a specific ship is completely sunk."""
    for row in player_boards[player_id]:
        if ship_symbol.upper() in row:  # Check if any part of the ship is still intact
            return False
    return True

def check_game_over(player_id):
    """Check if the game is over and send appropriate messages."""
    if ships_sunk[player_id] == len(ships):
        # Determine the winner
        winner_id = 1 - player_id
        winner_message = f"Player {winner_id + 1} Wins!"
        
        # Send game over message to both players
        game_over_msg = {"type": "game_over", "message": winner_message}
        for client in clients:
            client.send(pickle.dumps(game_over_msg))
        
        print(winner_message)
        return True
    return False

def handle_attack(conn, player_id, message):
    """Handles an attack from one player."""
    global turn

    opponent_id = 1 - player_id
    row, col = message["coords"]
    print(f"Player {player_id + 1} attacks ({row}, {col}) on Player {opponent_id + 1}'s board.")

    # Check if attack is valid
    if turn != player_id:
        conn.send(pickle.dumps({"type": "error", "message": "Not your turn."}))
        return

    # Check if the attack hits or misses
    target_cell = player_boards[opponent_id][row][col]
    if target_cell in ship_symbols.values():
        print(f"Hit! Player {player_id + 1} hit Player {opponent_id + 1}'s ship.")
        attack_boards[player_id][row][col] = "X"  # Mark hit on attack board
        player_boards[opponent_id][row][col] = player_boards[opponent_id][row][col].lower()  # Mark hit on opponent board
        conn.send(pickle.dumps({"type": "attack_result", "result": "hit", "coords": (row, col)}))
        clients[opponent_id].send(pickle.dumps({"type": "opponent_hit", "coords": (row, col)}))  # Notify defender

        # Check if the ship is sunk
        if is_ship_sunk(opponent_id, target_cell):
            print(f"Player {opponent_id + 1}'s ship {target_cell.upper()} has been sunk!")
            ships_sunk[opponent_id] += 1
            
            # Check if game is over
            if check_game_over(opponent_id):
                return
            
            # Notify both players about the sunk ship
            sunk_notification = {"type": "ship_sunk", "message": f"Player {player_id + 1} has sunk Player {opponent_id + 1}'s {target_cell.upper()}!"}
            for client in clients:
                client.send(pickle.dumps(sunk_notification))

            # Switch turn to the opponent
            turn = opponent_id
            notify_turn()
    else:
        print(f"Miss! Player {player_id + 1} missed.")
        attack_boards[player_id][row][col] = "*"  # Mark miss on attack board
        conn.send(pickle.dumps({"type": "attack_result", "result": "miss", "coords": (row, col)}))
        clients[opponent_id].send(pickle.dumps({"type": "opponent_miss", "coords": (row, col)}))  # Notify defender

    # Switch turn
    turn = opponent_id
    notify_turn()

def notify_turn():
    """Notify both players whose turn it is."""
    for i, client in enumerate(clients):
        if i == turn:
            print(f"Player {i + 1} notified: It's your turn.")
            client.send(pickle.dumps({"type": "your_turn"}))
        else:
            print(f"Player {i + 1} notified: Wait for your turn.")
            client.send(pickle.dumps({"type": "wait_turn"}))

def place_ship(board, row, col, length, orientation, symbol):
    """Place a ship on the board if the placement is valid."""
    if orientation == "H":
        if col + length > map_size or any(board[row][col + i] != "_" for i in range(length)):
            return False
        for i in range(length):
            board[row][col + i] = symbol
    elif orientation == "V":
        if row + length > map_size or any(board[row + i][col] != "_" for i in range(length)):
            return False
        for i in range(length):
            board[row + i][col] = symbol
    return True

# Initialize boards for both players
for i in range(2):
    player_boards[i] = [["_" for _ in range(map_size)] for _ in range(map_size)]
    attack_boards[i] = [["_" for _ in range(map_size)] for _ in range(map_size)]

# Accept connections from two clients
for player_id in range(2):
    try:
        client_socket, addr = server.accept()
        clients.append(client_socket)
        print(f"Player {player_id + 1} connected from {addr}")
        threading.Thread(target=handle_client, args=(client_socket, player_id)).start()
    except Exception as e:
        print(f"Error accepting connection for Player {player_id + 1}: {e}")
        traceback.print_exc()
