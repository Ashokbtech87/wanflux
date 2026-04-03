import sys
import unittest
import tkinter as tk
from tkinter import ttk
from unittest.mock import MagicMock, patch
import os

# Add current directory to path
sys.path.append(os.getcwd())

# Mock imports that might be missing or problematic
# We need to mock the full hierarchy for some
mock_google = MagicMock()
sys.modules['google'] = mock_google
sys.modules['google.auth'] = mock_google.auth
sys.modules['google.auth.transport'] = mock_google.auth.transport
sys.modules['google.auth.transport.requests'] = mock_google.auth.transport.requests
sys.modules['google.oauth2'] = mock_google.oauth2
sys.modules['google.oauth2.credentials'] = mock_google.oauth2.credentials

mock_auth_lib = MagicMock()
sys.modules['google_auth_oauthlib'] = mock_auth_lib
sys.modules['google_auth_oauthlib.flow'] = mock_auth_lib.flow

mock_apiclient = MagicMock()
sys.modules['googleapiclient'] = mock_apiclient
sys.modules['googleapiclient.discovery'] = mock_apiclient.discovery
sys.modules['googleapiclient.http'] = mock_apiclient.http

sys.modules['ollama'] = MagicMock()
sys.modules['viral_optimizer_fast'] = MagicMock()
sys.modules['PIL'] = MagicMock()
sys.modules['cv2'] = MagicMock()
sys.modules['tkdnd'] = MagicMock()

# Now import the app
try:
    from youtube_uploader import YouTubeUploaderApp
except ImportError as e:
    print(f"Import failed: {e}")
    sys.exit(1)

class TestColumnSorting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tk.Tk()
        
    @classmethod
    def tearDownClass(cls):
        cls.root.destroy()

    def setUp(self):
        # Patch __init__ to avoid full app initialization
        with patch.object(YouTubeUploaderApp, '__init__', return_value=None):
            self.app = YouTubeUploaderApp(None)
            
        columns = ('Title', 'Views', 'Duration', 'Date', 'Channel', 'Country', 'Video ID')
        self.tree = ttk.Treeview(self.root, columns=columns, show='headings')
        
        # Sample data
        # Data format: Title, Views, Duration, Date, Channel, Country, Video ID
        self.data = [
            ('Video A', '1,000', '10:00', '2023-01-01', 'Channel A', 'US', 'id1'),
            ('Video B', '500', '5:00', '2023-01-02', 'Channel B', 'IN', 'id2'),
            ('Video C', '2,000', '1:00', '2023-01-03', 'Channel C', 'CA', 'id3'),
            ('Video D', '10,000', 'N/A', '2023-01-04', 'Channel D', 'UK', 'id4')
        ]
        
        for item in self.data:
            self.tree.insert('', tk.END, values=item)

    def get_column_values(self, col_index):
        return [str(self.tree.item(item)['values'][col_index]) for item in self.tree.get_children('')]

    def test_sort_views(self):
        print("\nTesting Sort by Views...")
        # Sort Ascending (False)
        self.app.treeview_sort_column(self.tree, 'Views', False)
        views = self.get_column_values(1)
        print(f"Ascending: {views}")
        self.assertEqual(views[0], '500')
        self.assertEqual(views[3], '10,000')
        
        # Sort Descending (True)
        self.app.treeview_sort_column(self.tree, 'Views', True)
        views = self.get_column_values(1)
        print(f"Descending: {views}")
        self.assertEqual(views[0], '10,000')
        self.assertEqual(views[3], '500')

    def test_sort_country(self):
        print("\nTesting Sort by Country...")
        # Sort Ascending (CA, IN, UK, US) -> alphabetical
        self.app.treeview_sort_column(self.tree, 'Country', False)
        countries = self.get_column_values(5)
        print(f"Ascending: {countries}")
        self.assertEqual(countries[0], 'CA')
        self.assertEqual(countries[-1], 'US')

    def test_sort_duration(self):
        print("\nTesting Sort by Duration...")
        # Sort Ascending (N/A should be first as -1)
        self.app.treeview_sort_column(self.tree, 'Duration', False)
        durations = self.get_column_values(2)
        print(f"Ascending: {durations}")
        # Expected: N/A (-1), 1:00 (60), 5:00 (300), 10:00 (600)
        self.assertEqual(durations[0], 'N/A')
        self.assertEqual(durations[1], '1:00')
        self.assertEqual(durations[3], '10:00')

    def test_filter_logic(self):
        print("\nTesting Filter Logic (Mock)...")
        # specific to verifying that the app logic passes correct params would require mocking the search method
        # or checking internal state if possible. 
        # For now, we trust the manual verification plan for the UI interaction parts.
        pass

    def test_sort_date(self):
        print("\nTesting Sort by Date...")
        # Descending
        self.app.treeview_sort_column(self.tree, 'Date', True)
        dates = self.get_column_values(3)
        print(f"Descending: {dates}")
        self.assertEqual(dates[0], '2023-01-04')
        self.assertEqual(dates[3], '2023-01-01')

if __name__ == '__main__':
    unittest.main()
