

# File for performing unittests on data_tools.py

import unittest
from datetime import datetime, timezone
import pytz
import constants
import pickle
import mock

from data_tools import *

test_data_path = 'test_data'

class TestStringMethods(unittest.TestCase):

    def test_string_to_datetime(self):
        test_data = '12/18 10:12'
        test_year = datetime.now(timezone.utc).year
        test_datetime = string_to_datetime(test_data)
        actual_datetime = datetime(test_year, 12, 18, 10, 12, tzinfo=timezone.utc)
        self.assertEqual(test_datetime, actual_datetime)

    def test_web_to_list(self):
        web_page = pickle.loads(open(test_data_path + '/Sample_Tabular_Data_ARGW1_02.html', 'rb').read())
        test_list = web_to_list(web_page)

        # First, middle and last datapoint to check against
        actual_point_0 = (datetime(2022, 12, 18, 6, 0, tzinfo=timezone.utc), 2.48)
        actual_point_15 = (datetime(2022, 12, 22, 0, 0, tzinfo=timezone.utc), 2.19)
        actual_point_30 = (datetime(2022, 12, 25, 18, 0, tzinfo=timezone.utc), 4.69)

        self.assertEqual(test_list[0], actual_point_0)
        self.assertEqual(test_list[15], actual_point_15)
        self.assertEqual(test_list[30], actual_point_30)

class TestOutsideUserHours(unittest.TestCase):

    # Below is an example test pattern:
    #  test_before_begin 04:30 (False)  | user_start 05:00 | test_between_start_end 12:00 (True) | user_end 20:00 | 
    #  test_after_end 20:30 (True)

    # Tests 1-3 are for standard PST time

    
    def test_outside_user_hours_standard_PST_before_begin(self):

        user = {}
        user["timezone"] = "US/Pacific"
        user["start_hour"] = 5      
        user["end_hour"] = 20

        # 12:30 UTC = 04:30 PST
        current_time = datetime(2022, 12, 18, 12, 30, tzinfo=timezone.utc)

        self.assertEqual(outside_user_hours(user, current_time), True)

    def test_outside_user_hours_standard_PST_between_begin_end(self):

        user = {}
        user["timezone"] = "US/Pacific"
        user["start_hour"] = 5      
        user["end_hour"] = 20

        # 20:00 UTC = 12:00 PST
        current_time = datetime(2022, 12, 18, 20, 00, tzinfo=timezone.utc)

        self.assertEqual(outside_user_hours(user, current_time), False)
    
    def test_outside_user_hours_standard_PST_after_end(self):

        user = {}
        user["timezone"] = "US/Pacific"
        user["start_hour"] = 5      
        user["end_hour"] = 20

        # 04:30 UTC = 20:30 PST
        current_time = datetime(2022, 12, 18, 4, 30, tzinfo=timezone.utc)

        self.assertEqual(outside_user_hours(user, current_time), True)

    # Tests 4-6 are for standard PST time before, between, and after the user's hours

    def test_outside_user_hours_standard_PDT_before_begin(self):

        user = {}
        user["timezone"] = "US/Pacific"
        user["start_hour"] = 5      
        user["end_hour"] = 20

        # 11:30 UTC = 04:30 PDT
        current_time = datetime(2022, 6, 18, 11, 30, tzinfo=timezone.utc)

        self.assertEqual(outside_user_hours(user, current_time), True)

    def test_outside_user_hours_standard_PDT_between_begin_end(self):

        user = {}
        user["timezone"] = "US/Pacific"
        user["start_hour"] = 5      
        user["end_hour"] = 20

        # 19:00 UTC = 12:00 PDT
        current_time = datetime(2022, 6, 18, 19, 00, tzinfo=timezone.utc)

        self.assertEqual(outside_user_hours(user, current_time), False)

    def test_outside_user_hours_standard_PDT_after_end(self):

        user = {}
        user["timezone"] = "US/Pacific"
        user["start_hour"] = 5      
        user["end_hour"] = 20

        # 03:30 UTC = 20:30 PDT
        current_time = datetime(2022, 6, 18, 3, 30, tzinfo=timezone.utc)

        self.assertEqual(outside_user_hours(user, current_time), True)

    # Tests 7-9 are for inverted PST time before, between, and after the user's hours

    def test_outside_user_hours_inverted_PST_before_end(self):

        user = {}
        user["timezone"] = "US/Pacific"
        user["start_hour"] = 20      
        user["end_hour"] = 5

        # 12:30 UTC = 04:30 PST
        current_time = datetime(2022, 12, 18, 12, 30, tzinfo=timezone.utc)

        self.assertEqual(outside_user_hours(user, current_time), False)

    def test_outside_user_hours_inverted_PST_between_end_begin(self):

        user = {}
        user["timezone"] = "US/Pacific"
        user["start_hour"] = 20      
        user["end_hour"] = 5

        # 20:00 UTC = 12:00 PST
        current_time = datetime(2022, 12, 18, 20, 00, tzinfo=timezone.utc)

        self.assertEqual(outside_user_hours(user, current_time), True)

    def test_outside_user_hours_inverted_PST_after_begin(self):

        user = {}
        user["timezone"] = "US/Pacific"
        user["start_hour"] = 20      
        user["end_hour"] = 5

        # 04:30 UTC = 20:30 PST
        current_time = datetime(2022, 12, 18, 4, 30, tzinfo=timezone.utc)

        self.assertEqual(outside_user_hours(user, current_time), False)

    # Tests 10-12 are for exactly at start and end times

    def test_outside_user_hours_standard_PST_at_start(self):

        user = {}
        user["timezone"] = "US/Pacific"
        user["start_hour"] = 5      
        user["end_hour"] = 20

        # 13:00 UTC = 05:00 PST
        current_time = datetime(2022, 12, 18, 13, 00, tzinfo=timezone.utc)

        self.assertEqual(outside_user_hours(user, current_time), False)

    def test_outside_user_hours_standard_PST_at_end(self):
            
        user = {}
        user["timezone"] = "US/Pacific"
        user["start_hour"] = 5      
        user["end_hour"] = 20

        # 04:00 UTC = 20:00 PST
        current_time = datetime(2022, 12, 18, 4, 00, tzinfo=timezone.utc)

        self.assertEqual(outside_user_hours(user, current_time), False)


if __name__ == '__main__':
    unittest.main()