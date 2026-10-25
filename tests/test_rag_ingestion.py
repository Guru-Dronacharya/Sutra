"""Test Suite for Phase 5: Regulatory RAG Ingestion & Filtered Retrieval.
Traceability: REQ-4.1, REQ-4.2, REQ-4.3, REQ-4.4, REQ-4.5, REQ-4.6
"""

from pathlib import Path
import pytest
from services.common.database import SyncSessionLocal, init_db
from services.common.models import RegChunk, RegDocument
from services.rag.chunker import LegalStructureChunker
from services.rag.indexer import EmbeddingManager, RegulatoryIndexer, cosine_similarity
from services.rag.retriever import RegulatoryRetriever
from services.rag.tagger import MetadataTagger


@pytest.fixture(scope="module")
def setup_rag_fixture():
    init_db()
    db = SyncSessionLocal()
    indexer = RegulatoryIndexer()
    # Ingest corpus
    res = indexer.ingest_corpus(db)
    db.close()
    yield res


def test_req_4_1_corpus_presence_and_sample_labels():
    """REQ-4.1: Verify all 7 regulatory corpus documents exist and are strictly labelled 'SAMPLE – NOT OFFICIAL TEXT'."""
    corpus_files = [
        "corpus/dpdp_act_2023.txt",
        "corpus/dpdp_rules_2025.txt",
        "corpus/it_rules_2026.txt",
        "corpus/meity_guidelines_2025.txt",
        "corpus/rbi_free_ai_2025.txt",
        "corpus/eu_ai_act_2024.txt",
        "corpus/nist_ai_rmf_1_0.txt",
    ]
    for rel_path in corpus_files:
        path = Path(rel_path)
        assert path.exists(), f"Missing corpus file: {rel_path}"
        content = path.read_text(encoding="utf-8")
        assert "SAMPLE – NOT OFFICIAL TEXT" in content, f"File {rel_path} must be clearly marked SAMPLE – NOT OFFICIAL TEXT"
        assert "Decision-support information only; not legal advice." in content


def test_req_4_2_legal_structure_chunker():
    """REQ-4.2: Verify chunker splits text by Section boundaries preserving section IDs."""
    chunker = LegalStructureChunker()
    sample_text = """
[SECTION 4] Lawful Grounds
Personal data may be processed only for lawful purposes.

[SECTION 9] Children Data
A Data Fiduciary must obtain verifiable parental consent.
"""
    chunks = chunker.chunk_text(sample_text, "dpdp_act_2023")
    assert len(chunks) == 2
    assert chunks[0].section_id == "SECTION 4"
    assert chunks[1].section_id == "SECTION 9"
    assert "verifiable parental consent" in chunks[1].text


def test_req_4_3_metadata_tagging_rules():
    """REQ-4.3: Verify tagger maps clauses to frameworks and applicable risk tiers."""
    tagger = MetadataTagger()
    chunker = LegalStructureChunker()

    chunks = chunker.chunk_file("corpus/dpdp_act_2023.txt", "dpdp_act_2023")
    sec_9_chunk = next(c for c in chunks if c.section_id == "SECTION 9")
    tagged_9 = tagger.tag_chunk(sec_9_chunk)

    assert tagged_9["instrument"] == "Digital Personal Data Protection Act, 2023"
    assert "india" in tagged_9["frameworks"]
    assert "high" in tagged_9["tiers"]
    assert "prohibited" in tagged_9["tiers"]

    # Check EU AI Act tagging
    eu_chunks = chunker.chunk_file("corpus/eu_ai_act_2024.txt", "eu_ai_act_2024")
    art_5_chunk = next(c for c in eu_chunks if c.section_id == "ARTICLE 5")
    tagged_art_5 = tagger.tag_chunk(art_5_chunk)
    assert "eu" in tagged_art_5["frameworks"]
    assert "prohibited" in tagged_art_5["tiers"]


def test_req_4_4_embeddings_and_cosine_similarity():
    """REQ-4.4: Verify embedding manager produces normalized vectors and computes accurate cosine similarity."""
    embedder = EmbeddingManager()
    v1 = embedder.embed_text("Processing of children personal data under DPDP Act")
    v2 = embedder.embed_text("Verifiable parental consent for minors")
    v3 = embedder.embed_text("Automated stock trading latency optimization")

    assert len(v1) == 384
    assert len(v2) == 384

    # Related queries should have positive similarity
    sim_related = cosine_similarity(v1, v2)
    sim_unrelated = cosine_similarity(v1, v3)

    assert sim_related > 0.0
    assert sim_related >= sim_unrelated


def test_req_4_5_idempotent_indexing(setup_rag_fixture):
    """REQ-4.5: Verify corpus indexing is idempotent without duplicate entries."""
    db = SyncSessionLocal()
    doc_count_before = db.query(RegDocument).count()
    chunk_count_before = db.query(RegChunk).count()

    assert doc_count_before >= 7
    assert chunk_count_before >= 20

    # Re-run indexing
    indexer = RegulatoryIndexer()
    indexer.ingest_corpus(db)

    doc_count_after = db.query(RegDocument).count()
    chunk_count_after = db.query(RegChunk).count()

    assert doc_count_after == doc_count_before
    assert chunk_count_after == chunk_count_before
    db.close()


def test_req_4_6_framework_aware_tier_filtered_retrieval(setup_rag_fixture):
    """REQ-4.6: Verify filtered retrieval respects tier and framework boundaries."""
    db = SyncSessionLocal()
    retriever = RegulatoryRetriever()

    # Query 1: India-only framework filter must NEVER return EU AI Act chunks
    results_india = retriever.retrieve(
        db=db,
        query="prohibited practices and red lines",
        tier="prohibited",
        frameworks=["india"],
        top_k=10,
    )
    assert len(results_india) > 0
    for r in results_india:
        assert "eu" not in r["frameworks"]
        assert "prohibited" in [t.lower() for t in r["tiers"]]

    # Query 2: India + EU exposure profile includes EU AI Act Article 5
    results_india_eu = retriever.retrieve(
        db=db,
        query="social scoring and biometric surveillance",
        tier="prohibited",
        frameworks=["india", "eu"],
        top_k=10,
    )
    eu_found = any("ARTICLE 5" in r["section_id"] for r in results_india_eu)
    assert eu_found is True

    # Query 3: Low-tier retrieval filters out High-only provisions like Section 9 Children / Section 10 SDF
    results_low = retriever.retrieve(
        db=db,
        query="data processing requirements",
        tier="low",
        frameworks=["india"],
        top_k=10,
    )
    for r in results_low:
        assert "low" in [t.lower() for t in r["tiers"]]
        assert r["section_id"] != "SECTION 9"  # Children data is High/Prohibited only

    db.close()
