import os
import sys
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

try:
    from vector_store import PERSIST_DIRECTORY
except ImportError:
    print("❌ 导入 vector_store 失败，请检查文件位置。")
    sys.exit(1)

def inspect_db():
    ABSOLUTE_PATH = os.path.abspath(PERSIST_DIRECTORY)
    print(f"📂 正在读取数据库路径: {ABSOLUTE_PATH}")

    if not os.path.exists(PERSIST_DIRECTORY):
        print("❌ 错误: 数据库目录不存在！请检查路径或先运行一次 update_assets")
        return

    embedding_function = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )
    
    db = Chroma(
        collection_name="asset_reports",
        embedding_function=embedding_function,
        persist_directory=PERSIST_DIRECTORY
    )

    collection_data = db.get(limit=10)

    ids = collection_data['ids']
    metadatas = collection_data['metadatas']
    documents = collection_data['documents']

    print(f"\n✅ 数据库中共有 {len(ids)} 条记录 (本次展示前 {len(ids)} 条):\n")

    for i in range(len(ids)):
        print(f"--- 记录 {i+1} ---")
        print(f"🆔 ID: {ids[i]}")
        print(f"📅 Metadata (元数据): {metadatas[i]}")
        print(f"📄 Content (前100字符): {documents[i][:100]}...")
        print("-" * 30)

if __name__ == "__main__":
    inspect_db()