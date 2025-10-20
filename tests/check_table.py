import boto3

def check_table_structure():
    dynamodb = boto3.resource('dynamodb')
    client = boto3.client('dynamodb')
    
    try:
        # Get detailed information about the table
        response = client.describe_table(TableName='sagemind-metadata')
        table_info = response['Table']
        
        print("Table name:", table_info['TableName'])
        print("\nKey Schema:")
        for key in table_info['KeySchema']:
            print(f"- {key['AttributeName']}: {key['KeyType']}")
        
        if 'GlobalSecondaryIndexes' in table_info:
            print("\nGlobal Secondary Indexes:")
            for index in table_info['GlobalSecondaryIndexes']:
                print(f"- {index['IndexName']}")
                
    except Exception as e:
        print("Error:", str(e))

if __name__ == "__main__":
    check_table_structure() 