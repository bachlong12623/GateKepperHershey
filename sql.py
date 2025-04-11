import psycopg2
import configparser
from datetime import datetime

class SQL:
    def __init__(self):
        config = configparser.ConfigParser()
        config.read('config.ini')

        self.conn = psycopg2.connect(
            dbname=config['Database']['database_spk'],
            user=config['Database']['database_user'],
            password=config['Database']['database_password'],
            host=config['Database']['database_ip'],
            port=config['Database']['database_port']
        )
        self.cursor = self.conn.cursor()

    def insert_klippel(self, id, time, result, spl, imp, rbzharm, pol, ts, count_test):
        query = """
        INSERT INTO public.i_klippel(
            id, "time", result, spl, imp, rbzharm, pol, ts, count_test)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
        """
        self.cursor.execute(query, (id, time, result, spl, imp, rbzharm, pol, ts, count_test))
        self.conn.commit()

    def insert_output(self, id, time, result):
        query = """
        INSERT INTO public.i_output(
            id, "time", result)
        VALUES (%s, %s, %s);
        """
        self.cursor.execute(query, (id, time, result))
        self.conn.commit()
    
    def insert_p_output(self, id, time):
        query = """
        INSERT INTO public.p_output(
            id, "time", datecode)
        VALUES (%s, %s, '5V411A');
        """
        self.cursor.execute(query, (id, time))
        self.conn.commit()

    def close(self):
        self.cursor.close()
        self.conn.close()

def generate_ids(prefix, start, end):
    for i in range(start, end + 1):
        yield f"{prefix}{i:05}"

if __name__ == "__main__":
    sql = SQL()
    prefix = "EW1U9VKMNHY"
    start = 0
    end = 99999  # Adjust this range as needed

    for id in generate_ids(prefix, start, end):
        # sql.insert_klippel(id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), True, True, True, True, True, True, 1)
        # sql.insert_output(id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 1)
        sql.insert_p_output(id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print(f"Inserted {id} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    sql.close()