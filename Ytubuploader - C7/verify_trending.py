import unittest
from unittest.mock import MagicMock
from youtube_uploader import YouTubeSearcher

class TestYouTubeSearcher(unittest.TestCase):
    def test_get_trending_videos(self):
        # Mock the YouTube service
        mock_youtube = MagicMock()
        
        # Configure the mock chain
        # self.youtube.videos().list().execute()
        
        # mock_youtube.videos returns a mock (let's say M1)
        # M1() returns M1.return_value -> let's say M2 (the videos resource)
        # M2.list returns a mock (let's say M3)
        # M3() returns M3.return_value -> let's say M4 (the request)
        # M4.execute returns a mock (let's say M5)
        # M5() returns the result
        
        mock_videos_resource = mock_youtube.videos.return_value
        mock_list_method = mock_videos_resource.list
        mock_request = mock_list_method.return_value
        mock_execute = mock_request.execute
        
        # Scenario: Return 2 video IDs, but detailed response has them unsorted or sorted by ID
        # Let's say vid2 has fewer views than vid1
        mock_execute.side_effect = [
            {'items': [{'id': 'vid1'}, {'id': 'vid2'}], 'nextPageToken': None}, # First call for IDs
            {'items': [ # Second call for details - returning in arbitrary order
                {
                    'id': 'vid2',
                    'statistics': {'viewCount': '500', 'likeCount': '50'},
                    'snippet': {
                        'title': 'Test Video 2',
                        'description': 'Desc 2',
                        'publishedAt': '2023-01-01T00:00:00Z',
                        'tags': ['tag2'],
                        'categoryId': '22',
                        'channelTitle': 'Channel 2'
                    },
                    'contentDetails': {'duration': 'PT2M'}
                },
                {
                    'id': 'vid1',
                    'statistics': {'viewCount': '1000', 'likeCount': '100'},
                    'snippet': {
                        'title': 'Test Video 1',
                        'description': 'Desc 1',
                        'publishedAt': '2023-01-01T00:00:00Z',
                        'tags': ['tag1'],
                        'categoryId': '22',
                        'channelTitle': 'Channel 1'
                    },
                    'contentDetails': {'duration': 'PT1M'}
                }
            ]}
        ]
        
        searcher = YouTubeSearcher(mock_youtube)
        results = searcher.get_trending_videos(max_results=2)
        
        self.assertEqual(len(results), 2)
        # Should be sorted by views descending: vid1 (1000) then vid2 (500)
        self.assertEqual(results[0]['video_id'], 'vid1')
        self.assertEqual(results[0]['views'], 1000)
        self.assertEqual(results[1]['video_id'], 'vid2')
        self.assertEqual(results[1]['views'], 500)
        print("Successfully verified get_trending_videos logic and sorting!")

if __name__ == '__main__':
    unittest.main()
