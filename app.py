
import os

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv
from neo4j import GraphDatabase
from pyvis.network import Network

load_dotenv()

st.set_page_config(
    page_title="Tamil Nadu Agriculture KG",
    page_icon="🌾",
    layout="wide"
)


@st.cache_resource
def get_driver():
    driver = GraphDatabase.driver(
        os.getenv("NEO4J_URI"),
        auth=(
            os.getenv("NEO4J_USERNAME"),
            os.getenv("NEO4J_PASSWORD")
        )
    )
    driver.verify_connectivity()
    return driver


DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")


def query(cypher, **params):
    records, _, _ = get_driver().execute_query(
        cypher,
        database_=DATABASE,
        **params
    )
    return [record.data() for record in records]


st.title("🌾 Tamil Nadu Agriculture Knowledge Graph")
st.caption("PDF → OCR → Entities → Neo4j → Streamlit")

tab1, tab2, tab3 = st.tabs([
    "📊 Dashboard",
    "🔎 Search",
    "🕸️ Knowledge Graph"
])

with tab1:
    doc_count = query(
        "MATCH (d:Document) RETURN count(d) AS n"
    )[0]["n"]

    page_count = query(
        "MATCH (p:Page) RETURN count(p) AS n"
    )[0]["n"]

    crop_count = query(
        "MATCH (c:Crop) RETURN count(c) AS n"
    )[0]["n"]

    scheme_count = query(
        "MATCH (s:Scheme) RETURN count(s) AS n"
    )[0]["n"]

    a, b, c, d = st.columns(4)

    a.metric("Documents", doc_count)
    b.metric("Pages", page_count)
    c.metric("Crops", crop_count)
    d.metric("Schemes", scheme_count)

    st.subheader("Indexed documents")

    documents = query(
        """
        MATCH (d:Document)
        RETURN d.filename AS filename,
               d.source_url AS source_url
        ORDER BY filename
        LIMIT 100
        """
    )

    st.dataframe(
        pd.DataFrame(documents),
        use_container_width=True
    )


with tab2:
    st.subheader("Search agriculture documents")

    search_text = st.text_input(
        "Enter crop, scheme, or keyword",
        placeholder="Paddy, subsidy, நெல்..."
    )

    if search_text:
        results = query(
            """
            MATCH (d:Document)-[:HAS_PAGE]->(p:Page)
            WHERE toLower(p.text)
                  CONTAINS toLower($term)
            RETURN d.filename AS document,
                   p.number AS page,
                   substring(p.text, 0, 700)
                       AS excerpt,
                   d.source_url AS source_url
            LIMIT 30
            """,
            term=search_text
        )

        st.write("Matching pages:", len(results))

        for result in results:
            with st.expander(
                f"{result['document']} "
                f"- Page {result['page']}"
            ):
                st.write(result["excerpt"])

                if result["source_url"]:
                    st.markdown(
                        f"[Original PDF]"
                        f"({result['source_url']})"
                    )


with tab3:
    st.subheader("Explore graph relationships")

    records = query(
        """
        MATCH (d:Document)-[:HAS_PAGE]->(p:Page)
        MATCH (p)-[r]->(e)
        WHERE e:Crop OR e:Scheme
        RETURN d.filename AS document,
               p.id AS page_id,
               p.number AS page_no,
               type(r) AS relation,
               labels(e)[0] AS entity_type,
               e.name AS entity
        LIMIT 100
        """
    )

    net = Network(
        height="620px",
        width="100%",
        bgcolor="#ffffff",
        font_color="#222222",
        directed=True
    )

    added_nodes = set()

    def add_node(node_id, label, color):
        if node_id not in added_nodes:
            net.add_node(
                node_id,
                label=label,
                color=color,
                size=22
            )
            added_nodes.add(node_id)

    for row in records:
        doc_id = "doc:" + row["document"]
        page_id = row["page_id"]
        entity_id = (
            row["entity_type"] + ":" + row["entity"]
        )

        add_node(
            doc_id, row["document"][:24], "#2B6CB0"
        )
        add_node(
            page_id,
            "Page " + str(row["page_no"]),
            "#38A169"
        )
        add_node(
            entity_id,
            row["entity"],
            "#D69E2E"
        )

        net.add_edge(doc_id, page_id, label="HAS_PAGE")

        net.add_edge(
            page_id,
            entity_id,
            label=row["relation"]
        )

    if records:
        net.barnes_hut(
            gravity=-3500,
            central_gravity=0.2,
            spring_length=160
        )

        net.save_graph("agriculture_graph.html")

        with open(
            "agriculture_graph.html",
            encoding="utf-8"
        ) as html_file:
            components.html(
                html_file.read(),
                height=640,
                scrolling=True
            )
    else:
        st.info(
            "No extracted entity relationships yet. "
            "Check your entity vocabulary and PDFs."
        )
