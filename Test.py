import unittest
from unittest.mock import patch, MagicMock
import socket
import threading
import pickle

# Import the server and client modules
import server2 
import client2 

class TestBattleshipGame(unittest.TestCase):

    @patch('server2.socket.socket')
    def test_server_startup(self, mock_socket):
        """Test server startup and client connections."""
        mock_socket_instance = mock_socket.return_value
        mock_socket_instance.accept.side_effect = [
            (MagicMock(), ('127.0.0.1', 12345)),
            (MagicMock(), ('127.0.0.1', 12346))
        ]

        server_thread = threading.Thread(target=server2.main)
        server_thread.start()

        self.assertTrue(mock_socket_instance.bind.called)
        self.assertTrue(mock_socket_instance.listen.called)
        self.assertEqual(len(server2.clients), 2)

        server_thread.join()

    @patch('client2.socket.socket')
    def test_client_connection(self, mock_socket):
        """Test client connection to the server."""
        mock_socket_instance = mock_socket.return_value
        mock_socket_instance.recv.return_value = pickle.dumps({"type": "start", "player_id": 0})

        client_thread = threading.Thread(target=client2.main)
        client_thread.start()

        self.assertTrue(mock_socket_instance.connect.called)
        self.assertTrue(mock_socket_instance.recv.called)

        client_thread.join()

    @patch('server2.socket.socket')
    def test_ship_placement(self, mock_socket):
        """Test ship placement by a player."""
        mock_socket_instance = mock_socket.return_value
        mock_socket_instance.recv.side_effect = [
            pickle.dumps({"type": "place_ship", "ship": "Submarine", "coords": (0, 0), "orientation": "H"}),
            pickle.dumps({"type": "place_ship", "ship": "Submarine", "coords": (1, 0), "orientation": "V"})
        ]

        server_thread = threading.Thread(target=server2.main)
        server_thread.start()

        self.assertTrue(mock_socket_instance.send.called)
        self.assertIn("Submarine", server2.ship_placements[0])

        server_thread.join()

    @patch('server2.socket.socket')
    def test_attack_handling(self, mock_socket):
        """Test attack handling by a player."""
        mock_socket_instance = mock_socket.return_value
        mock_socket_instance.recv.side_effect = [
            pickle.dumps({"type": "attack", "coords": (0, 0)}),
            pickle.dumps({"type": "attack", "coords": (1, 1)})
        ]

        server_thread = threading.Thread(target=server2.main)
        server_thread.start()

        self.assertTrue(mock_socket_instance.send.called)
        self.assertEqual(server2.attack_boards[0][0][0], "X")

        server_thread.join()

    @patch('client2.socket.socket')
    def test_game_over(self, mock_socket):
        """Test game over scenario."""
        mock_socket_instance = mock_socket.return_value
        mock_socket_instance.recv.side_effect = [
            pickle.dumps({"type": "game_over", "message": "Player 1 Wins!"})
        ]

        client_thread = threading.Thread(target=client2.main)
        client_thread.start()

        self.assertTrue(mock_socket_instance.recv.called)
        self.assertTrue(client2.game_over)

        client_thread.join()

    @patch('server2.socket.socket')
    def test_invalid_ship_placement(self, mock_socket):
        """Test invalid ship placement by a player."""
        mock_socket_instance = mock_socket.return_value
        mock_socket_instance.recv.return_value = pickle.dumps({"type": "place_ship", "ship": "Submarine", "coords": (0, 0), "orientation": "H"})

        server_thread = threading.Thread(target=server2.main)
        server_thread.start()

        self.assertTrue(mock_socket_instance.send.called)
        self.assertNotIn("Submarine", server2.ship_placements[0])

        server_thread.join()

    @patch('server2.socket.socket')
    def test_duplicate_ship_placement(self, mock_socket):
        """Test duplicate ship placement by a player."""
        mock_socket_instance = mock_socket.return_value
        mock_socket_instance.recv.side_effect = [
            pickle.dumps({"type": "place_ship", "ship": "Submarine", "coords": (0, 0), "orientation": "H"}),
            pickle.dumps({"type": "place_ship", "ship": "Submarine", "coords": (1, 0), "orientation": "V"})
        ]

        server_thread = threading.Thread(target=server2.main)
        server_thread.start()

        self.assertTrue(mock_socket_instance.send.called)
        self.assertEqual(len(server2.ship_placements[0]), 1)

        server_thread.join()

    @patch('server2.socket.socket')
    def test_turn_switching(self, mock_socket):
        """Test turn switching between players."""
        mock_socket_instance = mock_socket.return_value
        mock_socket_instance.recv.side_effect = [
            pickle.dumps({"type": "attack", "coords": (0, 0)}),
            pickle.dumps({"type": "attack", "coords": (1, 1)})
        ]

        server_thread = threading.Thread(target=server2.main)
        server_thread.start()

        self.assertTrue(mock_socket_instance.send.called)
        self.assertEqual(server2.turn, 1)

        server_thread.join()

    @patch('client2.socket.socket')
    def test_ship_sunk_notification(self, mock_socket):
        """Test ship sunk notification to the client."""
        mock_socket_instance = mock_socket.return_value
        mock_socket_instance.recv.return_value = pickle.dumps({"type": "ship_sunk", "message": "Player 1 has sunk Player 2's Submarine!"})

        client_thread = threading.Thread(target=client2.main)
        client_thread.start()

        self.assertTrue(mock_socket_instance.recv.called)

        client_thread.join()

    @patch('client2.socket.socket')
    def test_wait_turn_notification(self, mock_socket):
        """Test wait turn notification to the client."""
        mock_socket_instance = mock_socket.return_value
        mock_socket_instance.recv.return_value = pickle.dumps({"type": "wait_turn", "message": "Waiting for your opponent's turn."})

        client_thread = threading.Thread(target=client2.main)
        client_thread.start()

        self.assertTrue(mock_socket_instance.recv.called)

        client_thread.join()

    @patch('client2.socket.socket')
    def test_your_turn_notification(self, mock_socket):
        """Test your turn notification to the client."""
        mock_socket_instance = mock_socket.return_value
        mock_socket_instance.recv.return_value = pickle.dumps({"type": "your_turn", "message": "It's your turn to attack!"})

        client_thread = threading.Thread(target=client2.main)
        client_thread.start()

        self.assertTrue(mock_socket_instance.recv.called)

        client_thread.join()

if __name__ == '__main__':
    unittest.main()
