import boto3
import json

def check_feedback_table():
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('SageMindFeedback')
    
    try:
        # Check if table exists
        table.table_status
        print(f"Table exists. Status: {table.table_status}")
        
        # Get table description
        response = table.meta.client.describe_table(
            TableName='SageMindFeedback'
        )
        print("\nTable description:")
        print(json.dumps(response, indent=2, default=str))
        
    except Exception as e:
        print(f"Error checking table: {str(e)}")

if __name__ == "__main__":
    check_feedback_table() 