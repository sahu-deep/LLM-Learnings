from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from openai import OpenAI


# Load environment variables
load_dotenv()

# OpenAI client
openai_client = OpenAI()


# Vector Embeddings
embedding_model = OpenAIEmbeddings(
    model="text-embedding-3-large"
)


# Connect to Qdrant
vector_db = QdrantVectorStore.from_existing_collection(
    url="http://localhost:6333",
    collection_name="node_js",
    embedding=embedding_model,
)


# Chat loop
while True:

    # Take user input
    user_query = input("\nAsk something: ")

    # Exit option
    if user_query.lower() in ["exit", "quit", "no"]:
        print("Goodbye! 👋")
        break

    # Search relevant chunks from vector DB
    search_results = vector_db.similarity_search(
        query=user_query
    )

    # Create context
    context = "\n\n\n".join([
        f"Page Content: {result.page_content}\n"
        f"Page Number: {result.metadata['page_label']}\n"
        f"File Location: {result.metadata['source']}"
        for result in search_results
    ])


    # System prompt
    SYSTEM_PROMPT = f"""
You are a helpful AI Assistant who answers user queries
based on the available context retrieved from a PDF file.

You should only answer the user based on the following context
and navigate the user to the correct page number to know more.

Context:
{context}
"""


    # Call OpenAI
    response = openai_client.chat.completions.create(
        model="gpt-5-mini",
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": user_query
            }
        ]
    )


    # Print response
    print(f"\n🤖: {response.choices[0].message.content}")


    # Ask whether user wants to continue
    again = input(
        "\nDo you want to ask another question? (yes/no): "
    )

    if again.lower() not in ["yes", "y"]:
        print("Goodbye! 👋")
        break