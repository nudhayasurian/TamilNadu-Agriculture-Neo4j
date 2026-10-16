
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

uri = os.getenv("NEO4J_URI")
username = os.getenv("NEO4J_USERNAME")
password = os.getenv("NEO4J_PASSWORD")
database = os.getenv("NEO4J_DATABASE", "neo4j")

driver = GraphDatabase.driver(
    uri,
    auth=(username, password)
)

try:
    driver.verify_connectivity()

    records, summary, keys = driver.execute_query(
        "RETURN 'Cloud connection successful' AS message",
        database_=database
    )

    print(records[0]["message"])

except Exception as error:
    print("Connection failed:", error)

finally:
    driver.close()
