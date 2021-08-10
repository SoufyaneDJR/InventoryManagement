from pymongo.mongo_client import MongoClient
CONNECTION_STRING = "mongodb+srv://soufyane:soufyane@cluster0.y6kgo.mongodb.net/mydatabase?retryWrites=true&w=majority"
client = MongoClient(CONNECTION_STRING)
db = client["mydatabase"]

