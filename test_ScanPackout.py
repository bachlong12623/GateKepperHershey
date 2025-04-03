import unittest

class TestScanPackout(unittest.TestCase):
    def test_example(self):
        date_code = '5VD02A'
        inner_date_code = '20251202'
        print("Year:", date_code[0])
        print("Month:", date_code[2])
        print("Date:", date_code[3:5])
        print("Year:", inner_date_code[3])
        print("Month:", inner_date_code[4:6])
        print('Date', inner_date_code[6:8])
        if not (date_code[0] == inner_date_code[3] and 
                    date_code[1] == 'V' and 
                    {'1': '01', '2': '02', '3': '03', '4': '04', '5': '05', 
                     '6': '06', '7': '07', '8': '08', '9': '09', 'O': '10', 
                     'N': '11', 'D': '12'}.get(date_code[2], '') == inner_date_code[4:6] and 
                    date_code[3:5] == inner_date_code[6:8]):
            print("Date code does not match inner date code")
        else:
            print("Date code matches inner date code")
           

if __name__ == "__main__":
    unittest.main()