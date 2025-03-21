import configparser

class QRCode:
    def __init__(self, code, work_order):
        
        
        self.work_order = work_order
        self.code = code.replace(" ", "")
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')
        self.vendor_code = self.config.get('Settings', 'vendor_code')
        self.vendor_name = self.config.get('Settings', 'vendor_name')
        self.part_number = self.config.get('Settings', 'pn')
        
    def is_valid_code(self):
        """
        Check if a given string is a valid inner code or not

        Parameters
        ----------
        code : str
            The code to be checked

        Returns 
        ------- 
        bool    
            True if the code is valid, False otherwise
        """
        code_parts = self.code.split('$')
        
        # Verify 1st part of the code
        if not self.is_valid_vendor_code(code_parts[0][:-10]):
            print('Vendor code is not valid')
            return False
        if not self.verify_id_inner_code(code_parts[0]):
            print('ID part is not valid')
            return False
        
        # Verify 2nd part of the code
        if not self.is_valid_vendor_code(code_parts[1]):
            print('Vendor code is not valid')
            return False
        
        # Verify 3rd part of the code
        if not self.is_valid_vendor_name(code_parts[2]):
            print('Vendor name is not valid')
            return False
        
        # Verify 4th part of the code
        if not self.is_valid_pn(code_parts[3]):
            print('Part number is not valid')
            print(code_parts[3])
            return False
        # Verify 5th part of the code
        if not self.is_valid_datecode(code_parts[5]):
            print('Datecode is not valid')
            return False
        self.quantity = code_parts[6]
        return True






    def is_valid_datecode(self, code_part):
        print(code_part)
        """
        Check if a given string is a valid datecode or not

        Parameters
        ----------
        code_part : str
            The code part to be checked

        Returns
        -------
        bool
            True if the datecode is valid, False otherwise
        """
        #check first 4 characters are year
        if not self.is_valid_year(int(code_part[:4])):
            print(code_part[:4])
            return False
        if not self.is_valid_month(int(code_part[4:6])):
            print(code_part[4:6])
            return False
        if not self.is_valid_day(int(code_part[6:8])):
            print(code_part[6:8])
            return False
        return True

    def is_valid_year(self, year):
        """
        Check if a given number is a valid year or not

        Parameters
        ----------
        year : int
            The number to be checked

        Returns
        -------
        bool
            True if the year is valid, False otherwise
        """
        if year < 1:
            return False
        if year > 9999:
            return False
        return True

    def is_valid_month(self, month):
        """
        Check if a given number is a valid month or not

        Parameters
        ----------
        month : int
            The number to be checked

        Returns
        -------
        bool
            True if the month is valid, False otherwise
        """
        if month < 1:
            return False
        if month > 12:
            return False
        return True

    def is_valid_day(self, day):
        """
        Check if a given number is a valid day or not

        Parameters
        ----------
        year : int
            The year of the date to be checked
        month : int
            The month of the date to be checked
        day : int
            The day of the date to be checked

        Returns
        -------
        bool
            True if the day is valid, False otherwise
        """
        if day < 1:
            return False
        if day > 31:
            return False
        return True

    def is_valid_vendor_code(self, code_part):
        """
        Check if a given string matches the vendor code

        Parameters
        ----------
        code_part : str
            The code part to be checked

        Returns
        -------
        bool
            True if the code part matches the vendor code, False otherwise
        """
        return code_part == self.vendor_code

    def verify_id_inner_code(self, code_part):
        """
        Verify the ID part of the inner code

        Parameters
        ----------
        code_part : str
            The code part to be checked

        Returns
        -------
        bool
            True if the ID part is valid, False otherwise
        """
        return (
            code_part[-2:].isdigit() and
            self.is_valid_datecode(code_part[-10:-2])
        )

    def is_valid_vendor_name(self, code_part):
    
        """
        Check if a given string matches the vendor name

        Parameters
        ----------
        code_part : str
            The code part to be checked

        Returns
        -------
        bool
            True if the code part matches the vendor name, False otherwise
        """
        return code_part == self.vendor_name
    
    def is_valid_pn(self, code_part):
        """
        Check if a given string matches the part number

        Parameters
        ----------
        code_part : str
            The code part to be checked

        Returns
        -------
        bool
            True if the code part matches the part number, False otherwise
        """
        return code_part == self.part_number
if __name__ == "__main__":
    code = '2025011501$$FOSTER$1370-HAE002R-17$25140001$YYYYMMDD$160'
    qr_code = QRCode(code)
    if qr_code.is_valid_code():
    #Example code: XXXXXXXX2025011501$XXXXXXXX$FOSTER$1370-HAE002R-17$25140001$YYYYMMDD$160
        print("The code is valid")
    else:
        print("The code is not valid")