import os
import sys
import json
import asyncio
#import boto3
import logging
from datetime import datetime
from typing import Dict, Set
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.clients.semantic_scholar import SemanticScholarClient

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MetadataEnricher:
    def __init__(self):
        #self.dynamodb = boto3.resource('dynamodb')
        #self.table = self.dynamodb.Table('research_embeddings')
        self.semantic_scholar = SemanticScholarClient()
        self.processed_pmids: Set[str] = set()
        self.success_count = 0
        self.error_count = 0
        
    async def enrich_all_items(self):
        """Enrich all items in the DynamoDB table with Semantic Scholar metadata"""
        try:
            # Get all items from DynamoDB
            response = self.table.scan()
            items = response['Items']
            total_items = len(items)
            
            logger.info(f"Found {total_items} items to process")
            
            for idx, item in enumerate(items, 1):
                try:
                    paper_id = item['paper_id']
                    chunk_id = item['chunk_id']
                    
                    # Skip if already processed this paper_id
                    if paper_id in self.processed_pmids:
                        logger.info(f"Skipping duplicate paper_id {paper_id}")
                        continue
                    
                    logger.info(f"Processing item {idx}/{total_items}: {chunk_id}")
                    
                    # Get existing metadata
                    try:
                        existing_metadata = json.loads(item.get('metadata', '{}'))
                    except:
                        existing_metadata = item.get('metadata', {})
                    
                    # Get new metadata from Semantic Scholar
                    citation_count = await self.semantic_scholar.get_citation_count(paper_id)
                    
                    # Update metadata
                    updated_metadata = existing_metadata.copy()
                    updated_metadata['citation_count'] = citation_count
                    updated_metadata['last_updated'] = datetime.now().isoformat()
                    
                    # Update DynamoDB
                    response = self.table.update_item(
                        Key={
                            'chunk_id': chunk_id,
                            'paper_id': paper_id  # Add paper_id to key
                        },
                        UpdateExpression='SET metadata = :m',
                        ExpressionAttributeValues={
                            ':m': updated_metadata
                        },
                        ReturnValues='UPDATED_NEW'
                    )
                    
                    logger.info(f"Updated {chunk_id} with citation count: {citation_count}")
                    self.processed_pmids.add(paper_id)
                    self.success_count += 1
                    
                except Exception as e:
                    logger.error(f"Error processing item {chunk_id}: {str(e)}")
                    self.error_count += 1
                    continue
            
            logger.info("\nEnrichment Complete!")
            logger.info(f"Successfully processed: {self.success_count}")
            logger.info(f"Errors encountered: {self.error_count}")
            logger.info(f"Unique papers processed: {len(self.processed_pmids)}")
            
        except Exception as e:
            logger.error(f"Error in enrichment process: {str(e)}")

async def main():
    enricher = MetadataEnricher()
    await enricher.enrich_all_items()

if __name__ == "__main__":
    asyncio.run(main()) 