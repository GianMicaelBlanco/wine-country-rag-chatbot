import streamlit as st
from snowflake.snowpark.context import get_active_session
import json

MODELS = ["llama3.3-70b", "mistral-large2", "claude-sonnet-4-5",
          "claude-haiku-4-5", "openai-gpt-5-mini", "llama3.1-70b",
          "llama3.1-8b", "mistral-7b"]
CHUNK_NUMBER = [4, 6, 8, 10, 12, 14, 16]

st.set_page_config(layout="wide")
session = get_active_session()

if "history" not in st.session_state:
    st.session_state.history = []

st.title(":wine_glass: California Wine Country Visit Assistant :wine_glass:")
st.caption("RAG chatbot built with Fivetran, Snowflake, Streamlit and Cortex.")

model = st.sidebar.selectbox("Select a Snowflake Cortex model:", MODELS, index=0)
use_rag = st.sidebar.checkbox("Use your Fivetran dataset as context?")
chunks = st.sidebar.selectbox("Number of context chunks:", CHUNK_NUMBER, index=1)

if st.button("Reset conversation"):
    st.session_state.history = []

question = st.text_input("Ask a question", placeholder="Message your CA Wine Country Visit Assistant...")

if question:
    with st.spinner("Thinking..."):
        try:
            used = []
            if use_rag:
                ctx_df = session.sql("""
                    select winery_or_vineyard, winery_information as winery_chunk,
                           vector_cosine_similarity(winery_embedding,
                               AI_EMBED('snowflake-arctic-embed-l-v2.0', ?)) as v_sim
                    from vineyard_data_vectors
                    order by v_sim desc
                    limit ?
                """, params=[question, chunks]).to_pandas()
                used = ctx_df["WINERY_OR_VINEYARD"].tolist()
                context = " ".join(ctx_df["WINERY_CHUNK"].tolist())
                prompt = ("Act as a California winery visit expert. Answer based only on the "
                          "context provided. Do not go outside the context.\n"
                          f"Context: {context}\nQuestion: {question}\nAnswer:")
            else:
                prompt = ("Act as a California winery visit expert. "
                          f"Question: {question}\nAnswer:")

            rows = session.sql("select AI_COMPLETE(?, ?) as response",
                               params=[model, prompt]).collect()
            response = rows[0][0]
            try:
                decoded = json.loads(response)
                if isinstance(decoded, str):
                    response = decoded
            except Exception:
                pass

            st.session_state.history.insert(0, (question, response, model, used))
        except Exception as e:
            st.warning(f"An error occurred: {e}")

for q, a, m, used in st.session_state.history:
    st.markdown(f":question: **You:** {q}")
    st.markdown(f":wine_glass: **Assistant ({m}):**")
    st.markdown(a)
    st.caption("RAG chunks used: " + (", ".join(used) if used else "none"))
    st.divider()
