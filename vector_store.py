import os
import logging
from typing import Dict, Any
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document

PERSIST_DIRECTORY = os.path.join(os.path.dirname(__file__), "chroma_db")

class AssetVectorDB:
    def __init__(self):
        self.embedding_function = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )

        self.vector_store = Chroma(
            collection_name="asset_reports",
            embedding_function=self.embedding_function,
            persist_directory=PERSIST_DIRECTORY
        )

    def add_report(self, report_text: str, metadata: Dict[str, Any]):
        try:
            clean_metadata = {
                k: v for k, v in metadata.items()
                if isinstance(v, (str, int, float, bool))
            }

            doc = Document(page_content=report_text, metadata=clean_metadata)

            self.vector_store.add_documents([doc])
            logging.info(f"Report stored in Vector DB with ID: {clean_metadata.get('report_date')}")

        except Exception as e:
            logging.error(f"Failed to store report in Vector DB: {e}")

    def similarity_search(self, query: str, k: int = 3):
        return self.vector_store.similarity_search(query, k=k)

asset_vector_db = AssetVectorDB()