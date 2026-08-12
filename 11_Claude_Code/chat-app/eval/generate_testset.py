import json
import os
import sys
from pathlib import Path

import nest_asyncio
nest_asyncio.apply()

from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent.parent))

REPO_PATH = os.getenv("REPO_PATH", "")

def load_documents():
    from langchain_community.document_loaders import TextLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    repo = Path(REPO_PATH)
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    docs = []

    candidates = [repo / "README.md"]
    candidates += sorted((repo / "packages").glob("*/README.md"))[:20]

    for p in candidates:
        try:
            raw = TextLoader(str(p), encoding="utf-8").load()
            docs.extend(splitter.split_documents(raw))
        except Exception as e:
            print(f"Skipping {p.name}: {e}")

    return docs

def main():
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings
    from ragas.testset import TestsetGenerator

    docs = load_documents()
    print(f"Loaded {len(docs)} document chunks from {REPO_PATH}")

    generator = TestsetGenerator.from_langchain(
        llm=ChatOpenAI(model="gpt-4o-mini"),
        embedding_model=OpenAIEmbeddings(),
    )

    testset = generator.generate_with_langchain_docs(docs, testset_size=15)
    records = testset.to_pandas().to_dict(orient="records")

    out = Path(__file__).parent / "test_cases.json"
    out.write_text(json.dumps(records, indent=2, default=str))
    print(f"Saved {len(records)} test cases to {out}")

if __name__ == "__main__":
    main()
