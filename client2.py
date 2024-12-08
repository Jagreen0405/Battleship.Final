# client.py
import socket
import pickle
import tkinter as tk
import tkinter.font as tkFont
from tkinter import messagebox
from queue import Queue
from threading import Lock

# Client setup
HOST = 'localhost'
PORT = 9999
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((HOST, PORT))

# Receive player ID and initialize board
initial_data = pickle.loads(client.recv(4096))  # Increased buffer size
player_id = initial_data["player_id"]
map_size = 10
player_board = [["_" for _ in range(map_size)] for _ in range(map_size)]
attack_board = [["_" for _ in range(map_size)] for _ in range(map_size)]
ships = {"Carrier": 5, "Battleship": 4, "Cruiser": 3, "Submarine": 2, "Destroyer": 2}
ship_symbols = {"Carrier": "C", "Battleship": "B", "Cruiser": "R", "Submarine": "S", "Destroyer": "D"}

placing_ship = None
orientation = "H"
phase = "placement"
your_turn = False
game_over = False

# GUI variables
ship_buttons = {}

# Tkinter setup for GUI
root = tk.Tk()
root.title(f"Battleship - Player {player_id + 1}")
root.geometry("800x600")
root.configure(bg="#2c3e50")

# Define styles for buttons and labels
button_font = tkFont.Font(family="Helvetica", size=10, weight="bold")
board_button_style = {"width": 2, "height": 1, "font": button_font, "bg": "#ecf0f1", "fg": "#2c3e50"}
hit_button_style = {"width": 2, "height": 1, "font": button_font, "bg": "#e74c3c", "fg": "#ecf0f1"}  # Red background for hits
miss_button_style = {"width": 2, "height": 1, "font": button_font, "bg": "#95a5a6", "fg": "#ecf0f1"}  # Gray background for misses
ship_button_style = {"font": button_font, "bg": "#3498db", "fg": "#ecf0f1", "activebackground": "#2980b9", "activeforeground": "#ecf0f1"}

# Frame setup for player board and attack board
player_frame = tk.Frame(root, bg="#2c3e50")
player_frame.grid(row=0, column=0, padx=10, pady=10)
border_frame = tk.Frame(root, width=10, bg="#2c3e50")  # Divider
border_frame.grid(row=0, column=1, sticky="ns")
attack_frame = tk.Frame(root, bg="#2c3e50")
attack_frame.grid(row=0, column=2, padx=10, pady=10)

# Notification label
notification_label = tk.Label(root, text="", bg="#2c3e50", fg="#ecf0f1", font=button_font)
notification_label.grid(row=2, column=0, columnspan=3, pady=10)

# Create button grids for player and attack boards
player_buttons = [[tk.Button(player_frame, **board_button_style) for _ in range(map_size)] for _ in range(map_size)]
attack_buttons = [[tk.Button(attack_frame, **board_button_style) for _ in range(map_size)] for _ in range(map_size)]

for row in range(map_size):
    for col in range(map_size):
        player_buttons[row][col].grid(row=row, column=col, padx=1, pady=1)
        attack_buttons[row][col].grid(row=row, column=col, padx=1, pady=1)

# Functions to handle ship placement and attacks
def select_ship(ship_name):
    """Set the ship that the player wants to place."""
    global placing_ship
    placing_ship = ship_name
    update_notification(f"{ship_name} selected. Click on the board to place it.")

def update_notification(message):
    """Update the notification label with a new message."""
    notification_label.config(text=message)

def send_place_ship(ship_name, row, col, orientation):
    """Send ship placement information to the server."""
    data = {
        "type": "place_ship",
        "ship": ship_name,
        "coords": (row, col),
        "orientation": orientation
    }
    client.send(pickle.dumps(data))
    print(f"Sent placement request for {ship_name} at ({row}, {col}) with orientation {orientation}")

def place_ship(row, col):
    """Callback function to handle ship placement on player's board."""
    global placing_ship, orientation, phase
    if phase != "placement" or not placing_ship:
        return
    send_place_ship(placing_ship, row, col, orientation)

def disable_ship_button(ship_name):
    """Disable the button for a ship after it is placed."""
    if ship_name in ship_buttons:
        ship_buttons[ship_name].config(state=tk.DISABLED)

def send_attack(row, col):
    """Send attack information to the server."""
    global your_turn, phase
    if game_over:
        update_notification("The game has ended!")
        return
    if phase != "combat" or not your_turn:
        update_notification("Please wait for your turn.")
        return
    if attack_board[row][col] != "_":
        update_notification("You've already attacked this position!")
        return
    data = {
        "type": "attack",
        "coords": (row, col)
    }
    client.send(pickle.dumps(data))
    print(f"Sent attack request for ({row}, {col})")
    your_turn = False  # Ensure the player cannot make another move until the turn is switched

def handle_attack_result(result, coords):
    """Update the attack board based on the result of the attack."""
    row, col = coords
    if result == "hit":
        attack_board[row][col] = "X"  # Mark hit on the dummy board
        attack_buttons[row][col].config(text="X", **hit_button_style)  # Update button style for hit
        update_notification("It's a hit!")
    else:
        attack_board[row][col] = "*"  # Mark miss on the dummy board
        attack_buttons[row][col].config(text="*", **miss_button_style)  # Update button style for miss
        update_notification("You missed!")
    update_boards()

def handle_opponent_hit(coords):
    """Update the player's main board when their ship is hit."""
    row, col = coords
    player_board[row][col] = "X"  # Mark the hit as "X" on the player's board
    player_buttons[row][col].config(text="X", **hit_button_style)  # Update button style for hit
    update_boards()

def handle_opponent_miss(coords):
    """Update the player's main board when the opponent misses."""
    row, col = coords
    player_board[row][col] = "*"  # Mark the miss as "*" on the player's board
    player_buttons[row][col].config(text="*", **miss_button_style)  # Update button style for miss
    update_boards()

def toggle_orientation():
    """Toggle ship orientation between horizontal and vertical."""
    global orientation
    orientation = "V" if orientation == "H" else "H"
    update_notification(f"Orientation set to {orientation}")

# Update boards in the GUI
def update_boards():
    """Refresh the GUI to display the current state of the player's and attack boards."""
    # Update player board
    for row in range(map_size):
        for col in range(map_size):
            btn_text = player_board[row][col]
            if btn_text == "X":
                player_buttons[row][col].config(text=btn_text, **hit_button_style)  # Update button style for hit
            elif btn_text == "*":
                player_buttons[row][col].config(text=btn_text, **miss_button_style)  # Update button style for miss
            else:
                player_buttons[row][col].config(text=btn_text)
            if phase == "placement":
                player_buttons[row][col].config(command=lambda r=row, c=col: place_ship(r, c))

    # Update attack board
    for row in range(map_size):
        for col in range(map_size):
            btn_text = attack_board[row][col]
            if btn_text == "X":
                attack_buttons[row][col].config(text=btn_text, **hit_button_style)  # Update button style for hit
            elif btn_text == "*":
                attack_buttons[row][col].config(text=btn_text, **miss_button_style)  # Update button style for miss
            else:
                attack_buttons[row][col].config(text=btn_text)
            if phase == "combat":
                attack_buttons[row][col].config(command=lambda r=row, c=col: send_attack(r, c))

def handle_opponent_hit(coords):
    """Update the player's main board when their ship is hit."""
    row, col = coords
    player_board[row][col] = "X"  # Mark the hit as "X" on the player's board
    player_buttons[row][col].config(text="X", **hit_button_style)  # Update button style for hit
    update_boards()

# Function to process incoming messages from the server
def receive_data():
    """Receive updates from the server and update the GUI accordingly."""
    global phase, your_turn
    while True:
        try:
            data = pickle.loads(client.recv(4096))  # Increased buffer size
            print(f"Player {player_id + 1} received: {data}")  # Debugging log
            
            # Use root.after to handle GUI updates in the main thread
            root.after(100, process_server_message, data)
            
        except EOFError:
            print("Server connection closed.")
            break
        except Exception as e:
            print(f"Error processing server data: {e}")
            break

def show_game_over_popup(message):
    """Display a custom Game Over popup with a larger size."""
    popup = tk.Toplevel(root)
    popup.title("Game Over")
    popup.geometry("400x200")  # Set the size of the popup
    popup.configure(bg="#2c3e50")

    label = tk.Label(popup, text=message, bg="#2c3e50", fg="#ecf0f1", font=("Helvetica", 16, "bold"))
    label.pack(pady=20)

    ok_button = tk.Button(popup, text="OK", command=popup.destroy, font=("Helvetica", 12, "bold"), bg="#3498db", fg="#ecf0f1")
    ok_button.pack(pady=10)

def process_server_message(data):
    """Process server messages in the main thread"""
    global phase, your_turn, game_over
    
    try:
        print(f"Processing message: {data}")  # Debugging log
        if isinstance(data, dict) and data["type"] == "game_over":
            game_over = True
            # Display the custom Game Over popup
            show_game_over_popup(data["message"])
            # Disable all buttons after game over
            disable_all_buttons()
            return
        elif isinstance(data, dict) and data["type"] == "ship_sunk":
            # Display the message as a popup
            messagebox.showinfo("Ship Sunk", data["message"])
        elif isinstance(data, dict) and data["type"] == "your_turn":
            your_turn = True
            update_notification(data.get("message", "It's your turn to attack!"))
            update_boards()
        elif isinstance(data, dict) and data["type"] == "wait_turn":
            your_turn = False
            update_notification(data.get("message", "Waiting for your opponent's turn."))
            update_boards()
        elif isinstance(data, dict) and data["type"] == "attack_result":
            handle_attack_result(data["result"], data["coords"])
            your_turn = False
        elif isinstance(data, dict) and data["type"] == "opponent_hit":
            handle_opponent_hit(data["coords"])
        elif isinstance(data, dict) and data["type"] == "opponent_miss":
            handle_opponent_miss(data["coords"])
        elif isinstance(data, dict) and data["type"] == "ship_placed":
            symbol, row, col, orientation = data["symbol"], *data["coords"], data["orientation"]
            place_ship_on_board(symbol, row, col, orientation)
            disable_ship_button(data["ship"])
            update_boards()
        elif isinstance(data, dict) and data["type"] == "all_ships_placed":
            update_notification("All ships placed! Waiting for opponent.")
            phase = "combat"
            update_boards()
        elif isinstance(data, dict) and data["type"] == "error":
            update_notification(data["message"])
    except Exception as e:
        print(f"Error processing message in GUI thread: {e}")

def handle_opponent_miss(coords):
    """Update the player's main board when the opponent misses."""
    row, col = coords
    player_board[row][col] = "*"  # Mark the miss as "*" on the player's board
    player_buttons[row][col].config(text="*", **miss_button_style)  # Update button style for miss
    update_boards()

def place_ship_on_board(symbol, row, col, orientation):
    """Update the player's board locally with the ship placement for display purposes."""
    # Map symbols back to ship lengths
    ship_lengths = {v: k for k, v in ship_symbols.items()}
    ship_name = ship_lengths[symbol]
    length = ships[ship_name]

    if orientation == "H":
        for i in range(length):
            player_board[row][col + i] = symbol
    elif orientation == "V":
        for i in range(length):
            player_board[row + i][col] = symbol

# Buttons for selecting ships and toggling orientation
ship_selection_frame = tk.Frame(root, bg="#2c3e50")
ship_selection_frame.grid(row=1, column=0, columnspan=3, pady=10)
tk.Label(ship_selection_frame, text="Select a Ship to Place:", bg="#2c3e50", fg="#ecf0f1", font=button_font).pack()

for ship_name in ships.keys():
    btn = tk.Button(ship_selection_frame, text=ship_name, command=lambda s=ship_name: select_ship(s), **ship_button_style)
    btn.pack(side=tk.LEFT, padx=5)
    ship_buttons[ship_name] = btn

tk.Button(ship_selection_frame, text="Toggle Orientation", command=toggle_orientation, **ship_button_style).pack(side=tk.LEFT, padx=5)

# Start receiving data from the server
import threading
threading.Thread(target=receive_data, daemon=True).start()

update_boards()
root.mainloop()

def disable_all_buttons():
    """Disable all buttons on both boards after game over."""
    for widget in player_frame.winfo_children():
        if isinstance(widget, tk.Button):
            widget.config(state=tk.DISABLED)
    for widget in attack_frame.winfo_children():
        if isinstance(widget, tk.Button):
            widget.config(state=tk.DISABLED)