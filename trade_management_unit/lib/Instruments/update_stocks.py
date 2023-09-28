import csv
import datetime
from trade_management_unit.models.Stock import Stock
class UpdateStock:
    def __init__(self):
        pass

    def update(self):
        create_list,update_list = self.__fetch_stock_list()
        self.__update_stock_list(create_list,update_list)


    def __fetch_stock_list(self):
        file = open('data/equity_list.csv')
        csvreader = csv.reader(file)
        header = next(csvreader) #To pop out first row 
        existing_stocks = Stock.objects.all().values_list('id', flat=True)
        update_list = []
        create_list = []
        for row in csvreader:
            stock_obj = self.__get_stock_object(row)
            if(stock_obj.id in existing_stocks):
                update_list.append(stock_obj)
            else:
                create_list.append(stock_obj)
        return create_list,update_list


    def __get_stock_object(self,row):
        stock_obj = Stock()
        stock_obj.nse_symbol = row[0]
        stock_obj.name = row[1]
        stock_obj.series = row[2]
        stock_obj.listing_date = self.__get_date(row[3])
        stock_obj.paid_up_value = int(row[4])
        stock_obj.market_lot = int(row[5])
        stock_obj.isin_number = row[6]
        stock_obj.face_value = int(row[7])
        stock_obj.id = stock_obj.isin_number
        return stock_obj
    

    def __get_date(self,date_string):
        format = '%d-%b-%Y'  # The format
        datetime_str = datetime.datetime.strptime(date_string, format)
        return datetime_str
    
    

    def __update_stock_list(self,create_list,update_list):       
        if(len(create_list)>0):
            Stock.objects.bulk_create(create_list)
        # Stock.objects.bulk_update(update_list)
        return
